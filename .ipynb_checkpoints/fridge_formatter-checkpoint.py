import pandas as pd
import re

def parse_fridge(name='fridge.txt'):
    with open(name, 'r', encoding='utf8') as f:
        fridge_data = [re.fullmatch(r'(?P<own>[+-]) (?P<wait>[!?.]) (?P<name>.*)', n.rstrip()).groupdict() for n in f.readlines()]
    return fridge_data

def normalise_fridge(fridge_data):
    return pd.DataFrame(fridge_data)