import re
import json

import mwclient
import wikitextparser as wtp
from tqdm import tqdm
import click

RECIPE_FORMAT = """
<noinclude>{{Table header profession}}</noinclude>{{Table row profession
  |level=70
  |icon=Crafting_Resource_Adeptselectuary.png
  |rarity=common
  |name=Adept's Electuary
  |link=Alchemy/Adept's Electuary
  |commission=7512
  |proficiency=800
  |focus=694-901
  |materials=6x {{itemlink|Wild Mint|*}}, 3x {{itemlink|Honey|*}}, 3x {{itemlink|Spring Water|*}}
  |tier1=3x {{itemlink|Adept's Electuary|*}}
  |tier2=3x {{itemlink|Adept's Electuary +1|*}}
  |tier3=
  |morale=40
  |interval=180
  |pxp=59973
}}<noinclude>|}[[Category:{{BASEPAGENAME}} tasks]]</noinclude>
"""

ITEM_FORMAT = """
{{ {{#if:{{{style|}}}
 |{{#ifexist:Template:Tooltip {{lc:{{{style}}}}}|Tooltip {{lc:{{{style}}}}}|TooltipItem}}
 |TooltipItem}}
  |{{#if:{{{1|}}}|{{{1}}}|Tooltip float box}}
  |title=Aberrant Blood
  |icon=Crafting_Resource_Aberrantblood.png
  |category=Profession Material
  |tag1=Substance
  |tag2=Material
  |quality=common
  |description=A phial of blood drawn from the corpse of an aberration.
  |value={{copper}}61
}}<noinclude>[[category:Tooltips]]</noinclude>
"""

PROFESSIONS = ["Gathering","Alchemy","Armorsmithing","Artificing","Blacksmithing","Jewelcrafting","Leatherworking","Tailoring"]

@click.group()
def cli():
    pass

def strip_itemlink(s):
  """Converts itemlink templates to text

  >>> strip_itemlink("6x {{itemlink|Wild Mint|*}}, 3x {{itemlink|Honey|*}}, 3x {{itemlink|Spring Water|*}}")
  '6x Wild Mint, 3x Honey, 3x Spring Water'

  """
  return s.replace("{{itemlink|","").replace("|*}}","")

def parse_quantity(s):
  """Parses quentity and item into an object

  >>> parse_quantity("1x {{itemlink|Leather Grimoire|*}}")
  {'quantity': 1, 'item': 'Leather Grimoire'}

  """
  s = s.strip().split(' ',1)
  q = int(s[0].strip('x')) if len(s) == 2 else 1
  i = strip_itemlink(s[1])
  return {'quantity': q, 'item': i}

def parse_value(raw):
  """ Extract values as total copper from gold/silver/coppr string

  >>> parse_value("{{copper}}61")
  61

  >>> parse_value("{{silver}}1 {{copper}}88")
  188

  """
  return int(raw.replace("{{silver}}","").replace("{{copper}}","").replace(" ","").strip())

def parse_profession_row(raw):
  """Parse a profession row/recipe into a recipe object

  >>> parse_profession_row(RECIPE_FORMAT)
  {'type': 'recipe', 'produces': [{'tier': 'tier1', 'quantity': 3, 'item': "Adept's Electuary"}, {'tier': 'tier2', 'quantity': 3, 'item': "Adept's Electuary +1"}], 'level': '70', 'icon': 'Crafting_Resource_Adeptselectuary.png', 'rarity': 'common', 'name': "Adept's Electuary", 'profession': 'Alchemy', 'commission': '7512', 'proficiency': '800', 'focus': '694-901', 'materials': [{'quantity': 6, 'item': 'Wild Mint'}, {'quantity': 3, 'item': 'Honey'}, {'quantity': 3, 'item': 'Spring Water'}], 'tier3': '', 'morale': '40', 'interval': '180', 'pxp': '59973'}

  """
  obj = {'type': 'recipe', 'produces':[]}
  parsed = wtp.parse(raw).templates
  row = [x for x in parsed if x.name.lower().startswith("table row profession")][0]
  for arg in row.arguments:
    if arg.name == 'materials':
      obj[arg.name] = [parse_quantity(x) for x in arg.value.split(",")]
    elif arg.name.startswith('tier') and arg.value.strip() != '':
      obj['produces'].append({'tier': arg.name.strip(),**parse_quantity(arg.value)})
    elif arg.name == 'link':
      obj['profession'] = arg.value.split('/')[0].strip()
    else:
      obj[arg.name] = arg.value.strip()
  return obj

def parse_item_tooltip(raw):
  """Parses an item into an object

  >>> parse_item_tooltip(ITEM_FORMAT)
  {'type': 'item', 'tags': ['Substance', 'Material'], 'title': 'Aberrant Blood', 'icon': 'Crafting_Resource_Aberrantblood.png', 'category': 'Profession Material', 'quality': 'common', 'description': 'A phial of blood drawn from the corpse of an aberration.', 'value': 61}

  """
  obj = {'type': 'item', 'tags':[]}
  parsed = wtp.parse(raw).templates[0]
  for arg in parsed.arguments:
    if arg.name.startswith("tag"):
        obj['tags'].append(arg.value.strip())
    elif arg.name.strip() == 'value':
      obj[arg.name.strip()] = parse_value(arg.value)
    elif arg.name.strip() == '1':
      continue
    else:
      obj[arg.name.strip()] = arg.value.strip()
  return obj

@cli.command()
@click.option('--recipes_file', default="recipes.jsonl", help='destination to save recipes to.')
@click.option('--items_file', default="items.jsonl", help='destination to save items to.')
def update_data(recipes_file,items_file):
  """fetches profession related materials and items from the neverwinter wiki"""
  site = mwclient.Site('neverwinter.gamepedia.com', path="/")

  with open(recipes_file, 'w') as recipe_out, open(items_file,'w') as item_out:
    for profession in PROFESSIONS:
      for item in tqdm(site.pages[profession].templates(), desc=f"Fetching items related to {profession}", unit=" items"):
        if item.name.endswith(f"/Tooltip"):
          obj = parse_item_tooltip(item.text())
          item_out.write(json.dumps(obj))
          item_out.write('\n')
        elif item.name.startswith(f"{profession}/"):
          obj = parse_profession_row(item.text())
          recipe_out.write(json.dumps(obj))
          recipe_out.write('\n')
        else:
          continue

if __name__ == '__main__':
    cli()
