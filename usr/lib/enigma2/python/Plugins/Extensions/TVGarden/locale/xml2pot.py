#!/usr/bin/python
# -*- coding: utf-8 -*-
# script: xml2pot.py (nella cartella principale del plugin)

import sys
import os
import re
try:
    import xml.etree.ElementTree as ET
except ImportError:
    import cElementTree as ET


def extract_strings_from_xml(xml_file):
    """Estrae tutte le stringhe da tradurre da setup.xml"""
    strings = []

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Cerca tutti i tag 'item' con attributi text/description
        for item in root.findall('.//item'):
            # Estrai attributo 'text'
            if 'text' in item.attrib:
                text = item.attrib['text'].strip()
                if text and not re.match(r'^#[0-9a-fA-F]{6,8}$', text):
                    strings.append(text)

            # Estrai attributo 'description'
            if 'description' in item.attrib:
                desc = item.attrib['description'].strip()
                if desc and not re.match(r'^#[0-9a-fA-F]{6,8}$', desc):
                    strings.append(desc)

        # Cerca anche nel tag 'setup' per il titolo
        for setup in root.findall('.//setup'):
            if 'title' in setup.attrib:
                title = setup.attrib['title'].strip()
                if title:
                    strings.append(title)

    except Exception as e:
        print("ERRORE nel parsing XML: %s" % str(e))
        return []

    # Rimuovi duplicati mantenendo l'ordine
    seen = set()
    unique_strings = []
    for s in strings:
        if s not in seen:
            seen.add(s)
            unique_strings.append(s)

    return unique_strings


def main():
    if len(sys.argv) < 2:
        print("Uso: python xml2pot.py <setup.xml>")
        sys.exit(1)

    # PERCORSI FISSI - NON CAMBIANO
    xml_file = "setup.xml"  # Nello stesso livello dello script
    pot_file = "locale/TVGarden.pot"  # Nella cartella locale/

    if not os.path.exists(xml_file):
        print("File non trovato: %s" % xml_file)
        print("Assicurati che xml2pot.py sia nella stessa cartella di setup.xml")
        sys.exit(1)

    # Estrai stringhe
    strings = extract_strings_from_xml(xml_file)

    if not strings:
        print("Nessuna stringa trovata in %s" % xml_file)
        sys.exit(0)

    print("Trovate %d stringhe uniche:" % len(strings))
    for i, text in enumerate(strings):
        print("%d. %s" % (i + 1, text[:80]))

    # Crea directory locale/ se non esiste
    if not os.path.exists("locale"):
        os.makedirs("locale")

    # Scrivi nel file .pot
    try:
        # Leggi contenuto esistente per evitare duplicati
        existing_strings = set()
        if os.path.exists(pot_file):
            with open(pot_file, 'r') as f:
                content = f.read()
                # Estrai tutti i msgid esistenti
                for match in re.finditer(r'msgid "([^"]+)"', content):
                    existing_strings.add(match.group(1))

        # Aggiungi solo nuove stringhe
        new_strings = [s for s in strings if s not in existing_strings]

        if not new_strings:
            print("\nTutte le stringhe sono già presenti in %s" % pot_file)
            return

        with open(pot_file, 'a') as f:
            f.write('\n# Strings from setup.xml\n')
            for text in new_strings:
                f.write('\n')
                f.write('msgid "%s"\n' % text.replace('"', '\\"'))
                f.write('msgstr ""\n')

        print(
            "\nAggiunte %d nuove stringhe a: %s" %
            (len(new_strings), pot_file))

    except Exception as e:
        print("ERRORE scrittura .pot: %s" % str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
