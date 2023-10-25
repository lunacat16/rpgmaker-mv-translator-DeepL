import argparse
import json
import os
import time

from deepl import Translator  # pip install deepl

from print_neatly import print_neatly


def translate(file_path, tr, src='EN', dst='KO', verbose=False, max_retries=5, max_len=55):
    def translate_sentence(text):
        target = text
        translation = tr.translate_text(target, source_lang=src, target_lang=dst).text
        text = translation
        if verbose:
            print(target, '->', translation)
        return text

    def translate_and_check(text, remove_escape=True, neatly=False, keep_space=True):
        text_tr = None
        if remove_escape:
            text = text.replace('\n', ' ')
        try:
            text_tr = translate_sentence(text)
        except:
            for _ in range(max_retries):
                try:
                    time.sleep(1)
                    text_tr = translate_sentence(text)
                except:
                    pass
                if text_tr is not None:
                    break
        if text_tr is None:
            print('Anomaly: {}'.format(text))
            return None, 0
        if neatly:
            try:
                text_neat = print_neatly(text_tr, max_len)
                if len(text_neat) > 1:
                    text_tr = text_neat[0] + '\n' + text_neat[1]
                else:
                    text_tr = text_neat[0]
            except:
                pass
        if keep_space:
            if text[0] == ' ' and text_tr[0] != ' ':
                text_tr = ' ' + text_tr
        return text_tr, 1

    def translate_based_on_keys(dict_or_list, keys, translations=0, remove_escape=True, neatly=False, array_translate=False):
        if isinstance(dict_or_list, dict):
            for d in dict_or_list:
                if isinstance(dict_or_list[d], dict) or isinstance(dict_or_list[d], list):
                    translations += translate_based_on_keys(dict_or_list[d], keys, translations, remove_escape, neatly, array_translate)
                elif d in keys and len(dict_or_list[d]) > 0:
                    tr, success = translate_and_check(dict_or_list[d], remove_escape, neatly)
                    dict_or_list[d] = tr
                    translations += success
        elif isinstance(dict_or_list, list):
            for i in range(len(dict_or_list)):
                if isinstance(dict_or_list[i], dict) or isinstance(dict_or_list[i], list):
                    translations += translate_based_on_keys(dict_or_list[i], keys, translations, remove_escape, neatly, array_translate)
                elif array_translate and isinstance(dict_or_list[i], str) and len(dict_or_list[i]) > 0:
                    tr, success = translate_and_check(dict_or_list[i], remove_escape, neatly)
                    dict_or_list[i] = tr
                    translations += success
        return translations

    translations = 0
    with open(file_path, 'r', encoding='utf-8-sig') as datafile:
        data = json.load(datafile)
    num_ids = len([e for e in data if e is not None])
    i = 0

    if file_path.endswith('GalleryList.json'):
        translations += translate_based_on_keys(data, ['displayName', 'hint', 'stageText', 'sceneText', 'text'], translations)
    
    elif file_path.endswith('RubiList.json'):
        translations += translate_based_on_keys(data, [], translations, array_translate=True)

    else:
        for d in data:
            if d is not None:
                print('{}: {}/{}'.format(file_path, i+1, num_ids))
                i += 1
                if 'name' in d.keys() and len(d['name']) > 0:
                    name_tr, success = translate_and_check(d['name'], remove_escape=True, neatly=False)
                    d['name'] = name_tr
                    translations += success
                if 'description' in d.keys() and len(d['description']) > 0:
                    desc_tr, success = translate_and_check(d['description'], remove_escape=True, neatly=True)
                    d['description'] = desc_tr
                    translations += success
                if 'profile' in d.keys() and len(d['profile']) > 0:
                    prf_tr, success = translate_and_check(d['profile'], remove_escape=True, neatly=True)
                    d['profile'] = prf_tr
                    translations += success
                # <speech/* : 대사> -> 대사 번역 구현
                for m in range(1, 5):
                    message = 'message' + str(m)
                    if message in d.keys() and len(d[message]) > 0:
                        message_tr, success = translate_and_check(d[message], remove_escape=False, neatly=False)
                        d[message] = message_tr
                        translations += success

    return data, translations


# usage: python objects_translator.py --source_lang it --dest_lang en --auth_key [YOUR_API_KEY] # do not type '[', ']'
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, default="objects")
    ap.add_argument("-sl", "--source_lang", type=str, default="")
    ap.add_argument("-dl", "--dest_lang", type=str, default="KO")
    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("-nf", "--no_format", action="store_true", default=False)
    ap.add_argument("-ml", "--max_len", type=int, default=40)
    ap.add_argument("-mr", "--max_retries", type=int, default=10)
    ap.add_argument("-api-key", "--auth_key", type=str, default="")
    args = ap.parse_args()
    dest_folder = args.input_folder + '_' + args.dest_lang
    translations = 0

    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    for file in os.listdir(args.input_folder):
        file_path = os.path.join(args.input_folder, file)
        if os.path.isfile(os.path.join(dest_folder, file)):
            print('skipped file {} because it has already been translated'.format(file_path))
            continue
        if file.endswith('.json'):
            print('translating file: {}'.format(file_path))
            new_data, t = translate(file_path, tr=Translator(args.auth_key), max_len=args.max_len,
                                    src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                    max_retries=args.max_retries)
            translations += t
            new_file = os.path.join(dest_folder, file)
            with open(new_file, 'w', encoding='utf-8') as f:
                if not args.no_format:
                    json.dump(new_data, f, indent=4, ensure_ascii=False)
                else:
                    json.dump(new_data, f, ensure_ascii=False)
    print('\ndone! translated in total {} strings'.format(translations))
