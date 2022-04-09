#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import glob
from bs4 import BeautifulSoup


def print_mist(out, mistakes):
    for m in mistakes:
        print('\t'.join(m))
        print('\t'.join(m), file=out)


def read_listwit(soup):
    wit = soup.find('listWit')
    listwit = ['#'+w['xml:id'] for w in wit.find_all('witness', {'xml:id':True})]
    return sorted(listwit)


def find_parentid(tag):
    parent_tag = tag.parent
    while parent_tag is not None:
        if 'xml:id' or 's' in parent_tag.attrs.keys():
            # print(parent_tag)
            return parent_tag.name, parent_tag.attrs
        parent_tag = parent_tag.parent
    return None


def get_and_validate_idlist(m_list, file_name, tag, tag_loc):
    if tag.attrs == {}:
        m_list.append((file_name, str(tag_loc), 'MISSING ATTRIBUTE!', tag.name, tag.text.replace('\n', '')[0:30]))
        return [False]
    else:
        id_list = tag['wit'].split()
        for i in id_list:
            if i.startswith('#') is False:
                m_list.append((file_name, str(tag_loc), f'# IS MISSING BEFORE THE VALUE: {i}', tag.text.replace('\n', '')[0:30]))
                return [False]
        return id_list


def find_mistakes(bs, curr_wit_list, mist, f_name):
    curr_wit = curr_wit_list
    bs_body = bs.find('body')
    for root in bs_body.find_all():
        has_app = root.find_all('app', recursive=False)
        if len(has_app) > 0:
            if root.name in {'lem', 'rdg'}:
                loc = find_parentid(root)
                if 'wit' in root.attrs:
                    curr_wit = sorted(root['wit'].split())
                    # print("CSERE !!!", loc, curr_wit)
                else:
                    # missing attribute!'
                    continue
            else:
                curr_wit = curr_wit_list

            for app in has_app:  # in bs.find_all('app', recursive=False):
                # <APP>
                upper_app_wits = {}
                loc = find_parentid(app)
                for i, lem_or_rdg in enumerate(app.find_all(['lem', 'rdg'], recursive=False)):
                    wits = get_and_validate_idlist(mist, f_name, lem_or_rdg, loc)
                    upper_app_wits[i] = wits
                upper_app_wits_sum = [item for sublist in upper_app_wits.values() for item in sublist]
                if False not in upper_app_wits_sum:
                    upper_app_wits_sum = sorted(upper_app_wits_sum)
                    if len(upper_app_wits_sum) != len(set(upper_app_wits_sum)):
                        mist.append((f_name, str(loc), 'DUPLICATED VALUE IN WITNESS SET:',
                                     str(upper_app_wits_sum), app.text.replace('\n', '')[0:30]))
                        # print(loc, upper_app_wits_sum)
                    elif upper_app_wits_sum != curr_wit:
                        print((f_name, str(loc), 'INCOMPLETE WITNESS SET! MISSING:',
                               str(set(curr_wit) - set(upper_app_wits_sum)), app.text[0:30]))
                        mist.append((f_name, str(loc), 'INCOMPLETE WITNESS SET! MISSING:',
                                     str(set(curr_wit) - set(upper_app_wits_sum)), app.text.replace('\n', '')[0:30]))

    return mist


if __name__ == '__main__':
    xml_folder = 'ransanus'
    output_filename = 'Ransanus_hiba.txt'
    mist_list = []
    with open(output_filename, 'a') as outf:
        #for filepath in glob.iglob('Kosztolanyi/*.xml'):
        for filepath in glob.iglob(f'{xml_folder}/*.xml'):
            print(filepath)
            with open(filepath, 'r') as xml_file:
                bs_xml = BeautifulSoup(xml_file, 'xml')
                curr_listwit = read_listwit(bs_xml)
                print(curr_listwit, len(curr_listwit))
                mist_list = find_mistakes(bs_xml, curr_listwit, mist_list, filepath)
        print("ERRRRRRRRROR >>>>>>>>>>>>>>>>>>>>yy")
        print_mist(outf, mist_list)
