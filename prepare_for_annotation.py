import os
import json
import spacy
import tqdm
nlp = spacy.load("en_core_web_trf")

from pathlib import Path
Path("corpus/wsd").mkdir(parents=True, exist_ok=True)

xml_content = "<?xml version='1.0' encoding='UTF-8'?>\n"
xml_content += '<corpus lang="en" source="exerciselibrary">\n'

corpus_files = [file for file in os.listdir("corpus/") if ".json" in file]

for json_file in tqdm.tqdm(corpus_files):
    with open("corpus/"+json_file, "r") as handle:
        content = json.load(handle)
        id = content['id']
        if 'action_text' in content:
            action_text = content['action_text']
            doc = nlp(action_text)

            xml_content += f'\t<text id="exerciselibrary.{id}">\n'

            sentence_counter = 0
            for sentence in doc.sents:
                xml_content += f'\t\t<sentence id="exerciselibrary.{id}.{sentence_counter}">\n'

                term_counter = 0
                for token in sentence:
                    pos_tag = token.pos_
                    lemma = token.lemma_
                    lemma = lemma.replace('"','&quot;').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    if 'VERB' in pos_tag or 'ADJ' in pos_tag or 'ADV' in pos_tag or 'NOUN' in pos_tag:
                        xml_content += f'\t\t\t<instance id="{id}.{sentence_counter}.{term_counter}" lemma="{lemma}" pos="{pos_tag}">{token.text}</instance>\n'
                    else:
                        xml_content += f'\t\t\t<wf lemma="{lemma}" pos="{pos_tag}">{token.text}</wf>\n'

                    term_counter += 1

                xml_content += '\t\t</sentence>\n'
                sentence_counter += 1

            xml_content += '\t</text>\n'

xml_content += '</corpus>'

with open('corpus/wsd/corpus-spacy.xml', 'w') as xml_file:
    xml_file.write(xml_content)
