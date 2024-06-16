import os
import stanza
import xml.etree.ElementTree as ET

from tqdm import tqdm
from lxml import etree
from typing import List, Tuple, Dict
from nltk.tokenize import sent_tokenize
from xml.etree.ElementTree import Element, SubElement, ElementTree


def get_xml_files(data_path: str) -> List:
    """
    :param data_path: Path to folder that contains the data files
    :return: Array with the filenames of the xml data files
    """
    filenames = os.listdir(data_path)
    xml_files = []
    for f in filenames:
        if f.split(".")[-1] == "xml":
            xml_files.append(f)
    return xml_files


def load_data(data_path: str, filenames: List) -> Tuple[List[str], List[List[Dict]], List]:
    """

    :param data_path: Path to folder that contains the data files
    :param filenames: Array with the filenames with want to load

    :return: cl_note_texts: Array with the clinical notes texts
            cl_note_events: Array of dictionaries with the attributes of all the events
            cl_note_tlinks: Array of dictionaries with the attributes of all the temporal links
    """

    cl_note_texts, cl_note_events, cl_note_tlinks = [], [], []

    for f in filenames:             # for all retrieved files
        parser = etree.XMLParser(recover=True)
        root = etree.parse(os.path.join(data_path, f), parser=parser)

        # Get the text
        text = root.find("TEXT").text.strip()
        # Remove new line symbols
        text = text.replace("\n", " ")

        cl_note_texts.append(text)

        sectimes = {}
        for s in root.find("TAGS").findall("SECTIME"):
            sectimes[s.attrib["type"]] = s.attrib["text"]

        # Extract the events
        events = []
        for event in root.find("TAGS").findall("EVENT"):
            event_values = dict(event.attrib.items())
            # event_values["event_type"] = "EVENT"
            event_values["SECTIME"] = False
            events.append(event_values)

        # Extract Timex3 events
        timexs = []
        for timex in root.find("TAGS").findall("TIMEX3"):
            timex_values = dict(timex.attrib.items())
            # timex_values["event_type"] = "TIMEX3"
            if timex_values["text"] in list(sectimes.values()):         # if timex_values["text"] is either admission or discahrge date
                index = list(sectimes.values()).index(timex_values["text"])
                timex_values["SECTIME"] = True
            else:
                timex_values["SECTIME"] = False
            timexs.append(timex_values)

        # Merge events and timex3s
        cl_note_events.append(events + timexs)

        # Extract Tlinks
        tlinks = []
        for link in root.find("TAGS").findall("TLINK"):
            tlinks.append(dict(link.attrib.items()))

        cl_note_tlinks.append(tlinks)

    return cl_note_texts, cl_note_events, cl_note_tlinks


def create_pair(head, tail):
    pair = {"char_span_start": min(int(tail["start"]), int(head["start"])),
            "char_span_end": max(int(tail["end"]), int(head["end"])),
            "fromID": head["id"],
            "fromText": head["text"],
            "fromStart": head["start"],
            "fromEnd": head["end"],
            "toID": tail["id"],
            "toText": tail["text"],
            "toStart": tail["start"],
            "toEnd": tail["end"],
            "sectime": head["SECTIME"] or tail["SECTIME"]           # todo - do we need it?
            }
    return pair


def get_event(e_id, events):
    found = False
    for e in events:
        if e["id"] == e_id:
            return e
    # Some error in the data had the text of the in the id field
    # In order to solve this will look for the event based on the text
    if not found:
        for e in events:
            if e["text"].upper() == e_id.upper():
                return e


def get_gold_pairs(ehr_events, ehr_tlinks):
    """

    :param ehr_events: Array of dictionaries with the attributes of all the events
    :param ehr_tlinks: Array of dictionaries with the attributes of all the temporal links
    :return: Array with the dictionaries of all the golds pairs for each EHR
    """

    # counter = 0
    ehr_gold_pairs = []
    for events, tlinks in zip(ehr_events, ehr_tlinks):
        # print("***********Report", counter)
        # counter += 1
        gold_pairs = []
        for tlink in tlinks:
            # print(tlink)
            head_id = tlink["fromID"]
            tail_id = tlink["toID"]
            # print(head_id)
            # print(tail_id)

            head = get_event(head_id, events)
            tail = get_event(tail_id, events)

            pair = {"char_span_start": min(int(tail["start"]), int(head["start"])),
                    "char_span_end": max(int(tail["end"]), int(head["end"])),
                    "tlinkID": tlink["id"],
                    "fromID": head["id"],
                    "fromText": head["text"],
                    "fromStart": head["start"],
                    "fromEnd": head["end"],
                    "toID": tail["id"],
                    "toText": tail["text"],
                    "toStart": tail["start"],
                    "toEnd": tail["end"],
                    "sectime": head["SECTIME"] or tail["SECTIME"]
                    }

            gold_pairs.append(pair)
        ehr_gold_pairs.append(gold_pairs)

    return ehr_gold_pairs


def get_dependency_tree(sentence, nlp_parser):
    # Parse the sentence
    doc = nlp_parser(sentence)
    # Check that the sentence is not tokenized
    assert len(doc.sentences) == 1, "Stanford parser tokenized the sentences"
    # Get the labeled words
    labeled_words = doc.sentences[0].words
    # Build the dependency tree
    tree, words = [], []
    for word in labeled_words:
        words.append(word.text)
        if word.head != 0:
            tree.append((word.deprel, word.head, word.id))

    return tree, words


def find_dependency(dependency_tree, head, tail):
    for dependency in dependency_tree:
        dep_relation, dep_head, dep_tail = dependency
        if dep_head == head and dep_tail == tail:
            return True
        if dep_tail == tail:
            # We use recursion to see if there are deeper dependencies beyond just the immediate head-dependent
            # e.g.: the dependent word is dependent on another word which itself is dependent on the head-word.
            if find_dependency(dependency_tree, head, dep_head):
                return True
    return False


def create_list_pairs(events, existing_pairs):
    pairs = []
    for i, e_id_head in enumerate(events[:-1]):
        for e_id_tail in events[i + 1:]:
            # print("Head sentence", e_id_head)
            # print("Tail sentence", e_id_tail)
            if (e_id_head, e_id_tail) not in existing_pairs and (e_id_tail, e_id_head) not in existing_pairs:
                if e_id_head[0] != "T" or e_id_tail[0] != "T":
                    pairs.append((e_id_head, e_id_tail))

    return pairs


def create_sentence_list_pairs(events):
    pairs = []
    for i, e_id_head in enumerate(events[:-1]):
        for e_id_tail in events[i + 1:]:
            # print("Head sentence", e_id_head)
            # print("Tail sentence", e_id_tail)
            if (len(e_id_head) != 0 and len(e_id_tail) != 0):
                if e_id_head[0] != "T" or e_id_tail[0] != "T":
                    pairs.append((e_id_head, e_id_tail))

    return pairs


def get_head_noun(text, nlp_parser):
    # Parse the sentence
    doc = nlp_parser(text)
    # Check that the sentence is not tokenized
    assert len(doc.sentences) == 1, "Stanford parser tokenized the sentences"
    # Get the labeled words
    labeled_words = doc.sentences[0].words
    head_noun = ""
    for w in labeled_words:
        if w.upos == "NOUN" and w.deprel == "root":
            head_noun = w.text

    return head_noun


def map_events_to_words(sentence, sentence_events, words, sentences, all_events):
    sentence_index = sentences.index(sentence)
    counter = 0
    for s in sentences[:sentence_index]:
        counter += len(s) + 1

    # if sentence[0] == " ":
    #     counter += 1

    # Find the positions for each word in the sentence
    word_pos = []

    for w in words:
        word_pos.append((counter + 1, counter + len(w) + 1))
        counter += len(w) + 1
        # print("Word:", w, "position:", (counter + 1, counter + len(w) + 1))

    # Find the words corresponding to each event
    events_to_words = {}
    for event_id in sentence_events:
        event_info = get_event(event_id, all_events)
        # print(event_id)
        # print(event_info)
        events_to_words[event_id] = []
        for i, w_p in enumerate(word_pos):
            if w_p[0] >= int(event_info["end"]):
                break
            if w_p[0] >= int(event_info["start"]) and w_p[1] <= int(event_info["end"]):
                events_to_words[event_id].append(i + 1)

    return events_to_words, word_pos


def filter_unique_pairs(event_pairs):
    unique_pairs = []
    unique_ids = []
    for pair in event_pairs:
        if (pair["fromID"], pair["toID"]) not in unique_ids:
            unique_pairs.append(pair)
            unique_ids.append((pair["fromID"], pair["toID"]))

    return unique_pairs


def get_candidate_pairs(ehr_texts, ehr_events, ehr_tlinks):
    """

    :param ehr_texts: Array with the texts of the EHRs
    :param ehr_events: Array of dictionaries with the attributes of all the events
    :param ehr_tlinks: Array of dictionaries with the attributes of all the temporal links
    :return: Array with the dictionaries of all the generated candidate pairs for each EHR
    """

    # Load the Stanford parser to find dependencies
    # stanza.download('en', package='craft')
    nlp_parser = stanza.Pipeline("en", package="craft", tokenize_no_ssplit=True)

    ehr_cnd_pairs = []
    for text, events, tlinks in tqdm(zip(ehr_texts, ehr_events, ehr_tlinks)):
        cnd_pairs = []
        eid_pairs = []

        # 1. Every event is paired to sectime
        print("Creating pairs with rule 1...")
        sectime_events = [e for e in events if e["SECTIME"] is True]              # admission and discharge events
        other_events = [e for e in events if e["SECTIME"] is False]                # other events

        for sectime in sectime_events:
            for event in other_events:
                if event["id"][0] != "T":
                    cnd_pairs.append(create_pair(event, sectime))
                    eid_pairs.append((event["id"], sectime["id"]))

        print("Rule 1 done")
        len1 = len(cnd_pairs)
        print("Found", len1, "pairs with rule 1")
        # End of rule 1

        # 2. All consecutive events within a sentence are paired
        print("Creating pairs with rule 2...")
        event_pos = {}

        for e in events:
            event_pos[e["id"]] = int(e["start"])

        # Order events by position
        event_pos = {k: v for k, v in sorted(event_pos.items(), key=lambda item: item[1])}

        sentences = sent_tokenize(text)
        startpoint = 0
        same_sentence_events = []
        for s in sentences:
            endpoint = startpoint + (len(s) - 1)

            # Find the events/times that are within this sentence
            same_sentence = []
            for et in event_pos:
                if startpoint <= event_pos[et] < endpoint:
                    same_sentence.append(et)
                elif event_pos[et] > endpoint:
                    break

            # Create consecutive pairs
            for i, ss in enumerate(same_sentence[:-1]):
                # Exclude Timex3-Timex3 pairs
                if (ss[0] != "T" or same_sentence[i + 1][0] != "T") and (ss, same_sentence[i + 1]) not in eid_pairs \
                        and (same_sentence[i + 1], ss) not in eid_pairs:
                    cnd_pairs.append(create_pair(get_event(ss, events), get_event(same_sentence[i + 1], events)))
                    eid_pairs.append((ss, same_sentence[i + 1]))

            same_sentence_events.append(same_sentence)
            startpoint = startpoint + (len(s) + 1)

        print("Rule 2 done")
        len2 = len(cnd_pairs)
        print("Found", len2 - len1, "pairs with rule 2")
        # End of rule 2

        # 3. Any events within one sentence that have a dependency relation are paired
        print("Creating pairs with rule 3...")

        for s, se in zip(sentences, same_sentence_events):
            # Get the dependency tree of the sentence
            dep_tree, words = get_dependency_tree(s, nlp_parser)
            # Check that the tokenization is aligned with the original sentence
            # assert " ".join(words) == s

            # Method that maps the labeled words to events
            e_ids_to_w_ids, word_pos = map_events_to_words(s, se, words, sentences, events)

            se_pairs = create_list_pairs(se, eid_pairs)
            for pair in se_pairs:
                dep_found = False
                w_ids_head = e_ids_to_w_ids[pair[0]]
                w_ids_tail = e_ids_to_w_ids[pair[1]]
                for id_head in w_ids_head:
                    for id_tail in w_ids_tail:
                        if find_dependency(dep_tree, id_head, id_tail) or find_dependency(dep_tree, id_tail, id_head):
                            cnd_pairs.append(
                                create_pair(get_event(pair[0], events), get_event(pair[1], events)))
                            eid_pairs.append((pair[0], pair[1]))
                            dep_found = True
                            break
                    if dep_found:
                        break
                if dep_found:
                    break

        print("Rule 3 done")
        len3 = len(cnd_pairs)
        print("Found", len3 - len2, "pairs with rule 3")
        # End of rule 3

        # 4. Pair the first and last events between two consecutive sentences
        print("Creating pairs with rule 4...")
        for i, ss in enumerate(same_sentence_events[:-1]):
            next_sentence_events = same_sentence_events[i + 1]
            if len(ss) != 0 and len(next_sentence_events) != 0:
                if (ss[0][0] != "T" or next_sentence_events[0][0] != "T") and (ss[0], next_sentence_events[0]) \
                        not in eid_pairs:
                    cnd_pairs.append(
                        create_pair(get_event(ss[0], events), get_event(next_sentence_events[0], events)))
                    eid_pairs.append((ss[0], next_sentence_events[0]))
                if (ss[0][0] != "T" or next_sentence_events[-1][0] != "T") and (ss[0], next_sentence_events[-1]) \
                        not in eid_pairs:
                    cnd_pairs.append(
                        create_pair(get_event(ss[0], events), get_event(next_sentence_events[-1], events)))
                    eid_pairs.append((ss[0], next_sentence_events[-1]))
                if (ss[-1][0] != "T" or next_sentence_events[0][0] != "T") and (ss[-1], next_sentence_events[0]) \
                        not in eid_pairs:
                    cnd_pairs.append(
                        create_pair(get_event(ss[-1], events), get_event(next_sentence_events[0], events)))
                    eid_pairs.append((ss[-1], next_sentence_events[0]))
                if (ss[-1][0] != "T" or next_sentence_events[-1][0] != "T") and (ss[-1], next_sentence_events[-1]) \
                        not in eid_pairs:
                    cnd_pairs.append(
                        create_pair(get_event(ss[-1], events), get_event(next_sentence_events[-1], events)))
                    eid_pairs.append((ss[-1], next_sentence_events[-1]))

        print("Rule 4 done")
        len4 = len(cnd_pairs)
        print("Found", len4 - len3, "pairs with rule 4")
        # End of rule 4

        # 5. Across multiple sentences: any two events with the same semantic type and the same head noun are paired
        print("Creating pairs with rule 5...")
        # start = time.time()
        # sentence_pairs = create_sentence_list_pairs(same_sentence_events)
        # for s_p in sentence_pairs:
        #     for e_id_head in s_p[0]:
        #         for e_id_tail in s_p[1]:
        #             if (e_id_head[0], e_id_tail[0]) not in eid_pairs and (e_id_tail[0], e_id_head[0]) not in eid_pairs:
        #                 if e_id_head[0] != "T" or e_id_tail[0] != "T":
        #                     # Check co-reference
        #                     head_info = get_event(e_id_head, events)
        #                     tail_info = get_event(e_id_tail, events)
        #                     h_noun_head = get_head_noun(head_info["text"], nlp_parser)
        #                     h_noun_tail = get_head_noun(tail_info["text"], nlp_parser)
        #                     if h_noun_head == h_noun_tail != "":
        #                         cnd_pairs.append(create_pair(head_info, tail_info))
        # end = time.time()

        # First pair the sentences
        # start = time.time()
        sentence_pairs = create_sentence_list_pairs(same_sentence_events)
        # Then, pair the events of each sentence pair
        epairs_across_sents = []
        for s_p in sentence_pairs:
            for e_id_head in s_p[0]:
                e_id_head_dupl = [e_id_head] * len(s_p[1])
                epairs_across_sents.extend(tuple(zip(e_id_head_dupl, s_p[1])))
        # Check co-reference
        for epair in epairs_across_sents:
            if (epair[0][0] != "T" or epair[1][0] != "T") and (epair[0], epair[1]) not in eid_pairs \
                    and (epair[1], epair[0]) not in eid_pairs:
                head_info = get_event(epair[0], events)
                tail_info = get_event(epair[1], events)
                h_noun_head = get_head_noun(head_info["text"], nlp_parser)
                h_noun_tail = get_head_noun(tail_info["text"], nlp_parser)
                if h_noun_head == h_noun_tail != "":
                    cnd_pairs.append(create_pair(head_info, tail_info))
        # end = time.time()


        print("Rule 5 done")
        len5 = len(cnd_pairs)
        print("Found", len5 - len4, "pairs with rule 5")
        # End of rule 5

        print("Found", len(cnd_pairs), "candidate pairs after applying the rules")

        # unique_cnd_pairs = filter_unique_pairs(cnd_pairs)
        # print(len(unique_cnd_pairs), "pairs are left after filtering out duplicates")

        ehr_cnd_pairs.append(cnd_pairs)

    return ehr_cnd_pairs


def save_pairs(filenames, report_pairs, name, mode):
    root = Element("Pairs")
    for filename, pairs in zip(filenames, report_pairs):
        report_element = SubElement(root, "Report", {"filename": filename})
        for p in pairs:
            if mode == "gold":
                pair_element = SubElement(report_element, "Pair", {"char_span_start": f'{p["char_span_start"]}',
                                                                   "char_span_end": f'{p["char_span_end"]}',
                                                                   "tlinkID": p["tlinkID"],
                                                                   "fromID": p["fromID"],
                                                                   "fromText": p["fromText"],
                                                                   "fromStart": p["fromStart"],
                                                                   "fromEnd": p["fromEnd"],
                                                                   "toID": p["toID"],
                                                                   "toText": p["toText"],
                                                                   "toStart": p["toStart"],
                                                                   "toEnd": p["toEnd"]})
            elif mode == "candidate":
                pair_element = SubElement(report_element, "Pair", {"char_span_start": f'{p["char_span_start"]}',
                                                                   "char_span_end": f'{p["char_span_end"]}',
                                                                   "fromID": p["fromID"],
                                                                   "fromText": p["fromText"],
                                                                   "fromStart": p["fromStart"],
                                                                   "fromEnd": p["fromEnd"],
                                                                   "toID": p["toID"],
                                                                   "toText": p["toText"],
                                                                   "toStart": p["toStart"],
                                                                   "toEnd": p["toEnd"]})
            else:
                print("Wrong mode! Select gold or candidates.")

    # Save xml
    tree = ElementTree(root)
    tree.write(name)


def load_pairs(pairs_file, files):
    # Read xml file
    tree = ET.parse(pairs_file)
    root = tree.getroot()

    reports = root.findall("Report")

    report_pairs = {}
    for r in reports:
        pairs = []
        for p in r.findall("Pair"):
            pairs.append({"char_span_start": f'{p.attrib["char_span_start"]}',
                          "char_span_end": f'{p.attrib["char_span_end"]}',
                          "tlinkID": p.attrib["tlinkID"],
                          "fromID": p.attrib["fromID"],
                          "fromText": p.attrib["fromText"],
                          "fromStart": p.attrib["fromStart"],
                          "fromEnd": p.attrib["fromEnd"],
                          "toID": p.attrib["toID"],
                          "toText": p.attrib["toText"],
                          "toStart": p.attrib["toStart"],
                          "toEnd": p.attrib["toEnd"]})
        report_pairs[r.attrib["filename"]] = pairs

    all_pairs = []
    for f in files:
        all_pairs.append(report_pairs[f])

    return all_pairs

def load_cnd_pairs(pairs_file, files):
    # Read xml file
    tree = ET.parse(pairs_file)
    root = tree.getroot()

    reports = root.findall("Report")

    report_pairs = {}
    for r in reports:
        pairs = []
        for p in r.findall("Pair"):
            pairs.append({"char_span_start": f'{p.attrib["char_span_start"]}',
                          "char_span_end": f'{p.attrib["char_span_end"]}',
                          "fromID": p.attrib["fromID"],
                          "fromText": p.attrib["fromText"],
                          "fromStart": p.attrib["fromStart"],
                          "fromEnd": p.attrib["fromEnd"],
                          "toID": p.attrib["toID"],
                          "toText": p.attrib["toText"],
                          "toStart": p.attrib["toStart"],
                          "toEnd": p.attrib["toEnd"]})
        report_pairs[r.attrib["filename"]] = pairs

    all_pairs = []
    for f in files:
        all_pairs.append(report_pairs[f])

    return all_pairs

def load_responses(resp_path):
    '''

    :param resp_path: Path to folder with the response files
    :return: Dictionary with response file and its responses
    '''

    files = os.listdir(resp_path)

    file_responses = {}
    for f in files:
        # Read xml file
        tree = ET.parse(os.path.join(resp_path, f))
        root = tree.getroot()

        relations = []
        for link in root.findall("TLINK"):
            relations.append({"id": link.attrib["id"], "fromID": link.attrib["fromID"],
                              "fromText": link.attrib["fromText"],
                              "toID": link.attrib["toID"],
                              "toText": link.attrib["toText"],
                              "type": link.attrib["type"]})
        file_responses[f] = relations

    return file_responses


