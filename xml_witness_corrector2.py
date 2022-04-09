#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import glob
import os
from os import makedirs
from io import StringIO
from xml.etree.ElementTree import ElementTree

from bs4 import BeautifulSoup
from os.path import basename, join as os_path_join

from io import StringIO
from xml.etree import ElementTree
from xml.dom import minidom
# from xml_irreg_finder import print_mist, get_listwit


def print_mist(out, mistakes):
    for m in mistakes:
        print('\t'.join(m))
        print('\t'.join(m), file=out)


def get_listwit(soup):
    wit = soup.find('listWit')
    listwit = ['#'+w['xml:id'] for w in wit.find_all('witness', {'xml:id': True})]
    return sorted(listwit)


def prettify_beta(xml_string):
    f = StringIO(xml_string)  # io.StringIO volt
    tree = ElementTree.parse(f)
    root = tree.getroot()
    teixml_as_string = ElementTree.tostring(root, encoding="unicode")
    xmlstr = minidom.parseString(teixml_as_string).toprettyxml(newl='\n', encoding='utf-8')
    xmlstr = os.linesep.join(s for s in xmlstr.decode("utf-8").splitlines() if s.strip())
    return xmlstr


def tei_writer(xml_string, origi_filename):
    misi_xml = prettify_beta(str(xml_string))
    pretty_new = '\n'.join([b.replace('ns0:', '') for b in misi_xml.split('\n')])
    odir = origi_filename.split('/')[0]
    newdir = f'{odir}_corrected'
    new_filename = origi_filename.split('/')[1]
    final_name = os_path_join(newdir, f'{new_filename}')
    makedirs(newdir, exist_ok=True)
    with open(final_name, 'w', encoding='utf-8') as open_file:
        open_file.write(str(pretty_new))


def find_parentid(tag):
    parent_tag = tag.parent
    while parent_tag is not None:
        if 'xml:id' or 's' in parent_tag.attrs.keys():
            # print(parent_tag)
            return parent_tag.name, parent_tag.attrs
        parent_tag = parent_tag.parent
    return None


def get_idlist(tag):
    if 'wit' in tag.attrs:
        return sorted(tag['wit'].split())
    return None


def first_fix(m_list, file_name, soup):
    id_list = []
    for tag in soup.find_all(['lem', 'rdg']):
        tag_loc = find_parentid(tag)
        if tag.attrs == {}:
            m_list.append(
                (file_name, str(tag_loc), 'WARNING / MISSING ATTRIBUTE!', tag.name, tag.text.replace('\n', '')[0:30]))
        else:
            id_list = tag['wit'].split()
            corr_id_list = []
            for i in id_list:
                if i.startswith('#') is False:
                    m_list.append((file_name, str(tag_loc), 'FIX / # IS MISSING BEFORE THE VALUE:', i,
                                   tag.text.replace('\n', '')[0:30]))
                    i = f'#{i}'
                elif not i[-1].isalnum():
                    m_list.append((file_name, str(tag_loc), 'WARNING / NOT VALID CHARACTER IN THE VALUE:', i,
                                   tag.text.replace('\n', '')[0:30]))
                corr_id_list.append(i)
            tag.attrs = {'wit': ' '.join(set(corr_id_list))}


def is_up_level(tag):
    haslem = tag.find(['lem', 'rdg'])
    if haslem is not None and haslem.find(['lem', 'rdg']) is not None:
        return True
    return False


def find_curr_target_set(tag):
    parent_tag = tag.parent
    while parent_tag is not None:
        if 'wit' in parent_tag.attrs.keys() and parent_tag.name in {'lem', 'rdg'}:
            return sorted(parent_tag['wit'].split())
        parent_tag = parent_tag.parent
    return None


def value_remover(dupl, error, f_name, loc, mist, sum_wit_set_app, wit_sets_per_app_dict):
    # egyesével kiveszem azokat, amik pluszban vannak benne
    for witval in dupl:
        if witval in wit_sets_per_app_dict[0][1]:
            wit_sets_per_app_dict[0][1].remove(witval)
            sum_wit_set_app.remove(witval)
            wit_sets_per_app_dict[0][0].attrs = {'wit': ' '.join(wit_sets_per_app_dict[0][1])}
        else:
            mist.append(
                (f_name, str(loc), error, witval))


def find_mistakes(bs, main_wit_list, mist, f_name):
    """Fő funkció: Ellenőrzi, hogy az egyes <app> részfákban a <lem> és <rdg>-kben "wit" attribútumában található
    id halmazok match-elnek-e az <app> legközelebbi szülő <lem>/<rdg>-jében vagy a legfelső szint esetén a header-ben
    felsorolt witness halmazzal
    Hibák lehetnek: 1) egyszerű duplikáció(k)
                    2) olyan id, amelynek azon az ágon már nem szabadna felbukkania
                    3) hiányzó id(k):a közvetlen szülő id halmazához képest hiányzik
    Automatikus korrekció:
        id-k törlése: akkor van megengedve, ha a <lem>-ből tudja kivennei a felesleget  (ha nem, akkor WARNING)
        id hozzáadása: mindig a <lem>-hez
        (ha van lem, akkor ahhoz,. ha csak redg, akkor a legelső rdg-hez)
    # TODO: fájlban maradt kommentek előszűrése: dobja vissza a fájlt rögtön
    # TODO: tudjon rdg-ből is kivenni felesleget, amennyiben az attribútuma nem marad teljesen érték nélkül
                                    (problémás, hogy melyik rdg-ből, ha választani kell!)
                    """

    bs_body = bs.find('body')
    """1) alap bakik"""
    first_fix(mist, f_name, bs)

    """2)"""
    for app in bs_body.find_all('app'):
        curr_target_witness_set = find_curr_target_set(app)
        if curr_target_witness_set is None:
            curr_target_witness_set = main_wit_list
        loc = find_parentid(app)
        wit_sets_per_app_dict = {}
        sum_wit_set_app = []

        for i, lem_or_rdg in enumerate(app.find_all(['lem', 'rdg'], recursive=False)):
            wits = get_idlist(lem_or_rdg)
            if wits is not None:
                wit_sets_per_app_dict[i] = (lem_or_rdg, wits)
                sum_wit_set_app.extend(wits)

        sum_wit_set_app = sorted(sum_wit_set_app)
        if sum_wit_set_app != curr_target_witness_set:
            diff_extra = set(sum_wit_set_app) - set(curr_target_witness_set)
            # azért if-ek következnek, mert egy résszel több probléma lehet, ebben a sorrendben kell megoldani,
            # a korrigált megy a kövi szűrőbe
            if len(diff_extra) > 4:
                # csak jelzés, ha sokkal több érték van az alsóbb szinten, mint amit a gyökere megenged
                mist.append((f_name, str(loc), 'WARNING / TOO MUCH EXTRA (LOWER-LEVEL) VALUES',
                             str(curr_target_witness_set), str(sum_wit_set_app)))
            if sorted(sum_wit_set_app) != sorted(list(set(sum_wit_set_app))):
                dupl = set([d for d in sum_wit_set_app if sum_wit_set_app.count(d) > 1])
                mist.append((f_name, str(loc), 'FIX / ONE OR MORE DUPLICATION IN:', str(sum_wit_set_app),
                             app.text.replace('\n', ' ')[0:30]))
                error = 'WARNING / ONE OR MORE DUPLICATION <--- NOT SOLVED'
                value_remover(dupl, error, f_name, loc, mist, sum_wit_set_app, wit_sets_per_app_dict)

            diff_extra = set(sum_wit_set_app) - set(curr_target_witness_set)
            if len(diff_extra) > 0:
                diff_extra = set(sum_wit_set_app) - set(curr_target_witness_set)
                mist.append((f_name, str(loc), 'FIX / ONE OR MORE EXTRA WITNESS IN SET:', str(diff_extra),
                             app.text.replace('\n', ' ')[0:30]))
                error = 'WARNING / "ONE OR MORE EXTRA WITNESS IN SET <--- NOT SOLVED'
                for extra in diff_extra:
                    # egyesével kiveszem azokat, amik pluszban vannak benne
                    value_remover(extra, error, f_name, loc, mist, sum_wit_set_app, wit_sets_per_app_dict)

            diff_set = set(curr_target_witness_set) - set(sum_wit_set_app)
            if len(diff_set) > 0:
                mist.append((f_name, str(loc), 'FIX / INCOMPLETE WITNESS SET! MISSING:', str(diff_set),
                             app.text.replace('\n', ' ')[0:30]))
                tag_to_correct = wit_sets_per_app_dict[0][0]
                corrected_set = set(wit_sets_per_app_dict[0][1]).union(diff_set)
                tag_to_correct.attrs = {'wit': ' '.join(corrected_set)}

    return bs, mist


if __name__ == '__main__':
    # xml_folder = 'ransanus_check'
    xml_folder = 'ransanus'
    output_filename = f'{xml_folder}_FIX_log.txt'
    mist_list = []
    with open(output_filename, 'a') as outf:
        for filepath in glob.iglob(f'{xml_folder}/*.xml'):
            with open(filepath, 'r') as xml_file:
                bs_xml = BeautifulSoup(xml_file, 'xml')
                curr_listwit = get_listwit(bs_xml)
                corrected_bs, mist_list = find_mistakes(bs_xml, curr_listwit, mist_list, filepath)
                tei_writer(corrected_bs, filepath)
        print_mist(outf, mist_list)
