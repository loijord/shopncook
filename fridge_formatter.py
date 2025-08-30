import pandas as pd
import re

def parse_fridge(name='fridge.csv'):
    pd.read_csv(name='fridge.csv')

def normalise_fridge(fridge_data):
    return pd.DataFrame(fridge_data)