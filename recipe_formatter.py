import re
import pandas as pd

def expand(command_line, pattern, captures=[], last=True):
    def mapper(m):
        key = m.group(0)
        val = pattern[key]
        if key in captures:
            return f'(?P<{key}>{val})'
        else:
            if last:
                return val
            else:
                return f'({val})'
    
    script = re.sub("|".join(pattern.keys()), mapper, command_line)
    if last:
        return script.replace(' ', '')
    else:
        return script

s1 = expand(r'\*\s (quantity \s)? name (\s argsenv)?', 
            pattern=dict(quantity = r'amount (\s? units)?',
                         argsenv = r'\[ args \]'),
            captures=[], last=False)

s2 = expand(s1, 
            pattern = dict(amount = r'\d+\.?\d*', 
            units='|'.join(['ml', 'l', 'g', 'kg', 'vnt', 'vnt.']), 
            name=r'([a-zA-Ząčęėįšųūž]+\s)*[a-zA-Ząčęėįšųūž]+',
            args='.+'), 
            captures=['amount', 'units', 'name', 'args'])

s3 = expand(r'amount \s? units', 
            pattern = dict(
                amount = r'\d+\.?\d*', 
                units='|'.join(['ml', 'l', 'g', 'kg', 'vnt', 'vnt.'])),
            captures=['amount', 'units'])

def match_args(args):
    '''"item: arbūzas, weight: 200g" -> {'type': 'item', 'name': 'arbūzas', 'amount': '200', 'units': 'vnt'}'''
    weight_pattern = expand(r'amount \s? units', 
                            pattern = dict(amount = r'\d+\.?\d*', 
                                           units='|'.join(['ml', 'l', 'g', 'kg'])),
                            captures=['amount', 'units'])
    d = dict()
    for s in args.split(', '):
        arg, val = s.split(': ')
        if arg in ('item', 'recipe'):
            d['name'] = val
            d['type'] = arg
        elif arg == 'weight':
            d = {**d, **re.fullmatch(weight_pattern, val).groupdict()}
    return d

def match_recipe_line(line, default_type='item'):
    #like: `* 200gr ridikėlių [item: ridikėliai]` arba `* 2 paprikos [weight: 150g]`
    s1 = expand(r'\*\s header (\s argsenv)?', 
               pattern=dict(header = r'(quantity \s)? name',
                            argsenv = r'\[ args \]'),
               captures=['header'], last=False)

    s2 = expand(s1, 
                pattern = dict(quantity = r'amount (\s? units)?',
                               name=r'([a-zA-Ząčęėįšųūž]+\s)*[a-zA-Ząčęėįšųūž]+',
                               args='.+'), 
                captures=['name', 'args'], last=False)
    recipe_pattern = expand(s2,
                            pattern = dict(amount = r'\d+\.?\d*', 
                                           units='|'.join(['ml', 'l', 'g', 'kg', 'vnt', 'vnt.'])),
                            captures=['amount', 'units'])
    match = re.fullmatch(recipe_pattern, line)
    if match:
        d = match.groupdict()
        if d['args']:
            d = {**d, **match_args(d['args'])}
        if 'type' not in d:
            d['type'] = default_type
        d.pop('args')
        return d
    else:
        raise ValueError(f'line = {line} does not match')

def parse_recipe(name):
    with open(name, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        recipe_ingredients = []
        for line in lines:
            line = line.rstrip()
            if line.startswith('*'):
                recipe_ingredients.append(match_recipe_line(line, default_type='item'))
            elif line.startswith(' ') or line.startswith('\t'):
                if 'details' not in recipe_ingredients[-1]:
                    recipe_ingredients[-1]['details'] = []
                recipe_ingredients[-1]['details'].append(match_recipe_line(line.lstrip()))
            else:
                raise ValueError('Unexpected start character in line:, line')     
    return recipe_ingredients

def normalise_recipe(recipe_data):
    df = pd.DataFrame([{'amount': ingredient['amount'], 
                        'units': ingredient['units'], 
                        'name': ingredient['name']} for ingredient in recipe_data])
    
    df['amount'] = df['amount'].astype(float)

    #fix rows where weight is g:
    is_g = df['units'] == 'g'
    df.loc[is_g, 'amount'] = df.loc[is_g, 'amount'] / 1000
    df.loc[is_g, 'units'] = 'kg'

    #fix rows where weight is ml:
    is_ml = df['units'] == 'ml'
    df.loc[is_ml, 'amount'] = df.loc[is_ml, 'amount'] / 1000
    df.loc[is_ml, 'units'] = 'l'

    df['name'] = df['name'].map(lambda x: x[:1].upper() + x[1:])
    has_amount = df['amount'].notnull()
    has_no_units = df['units'].isnull()
    df.loc[has_amount & has_no_units, 'units'] = 'vnt.'
    return df