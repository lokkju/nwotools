import re
import json

import mwclient
import wikitextparser as wtp
from tqdm import tqdm
import click

src = """
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

PROFESSIONS = ["Gathering","Alchemy","Armorsmithing","Artificing","Blacksmithing","Jewelcrafting","Leatherworking","Tailoring"]
@click.group()
def cli():
    pass


def strip_itemlink(s):
  return s.replace("{{itemlink|","").replace("|*}}","")

def parse_profession_row(raw):
  obj = {'type': 'recipe'}
  parsed = wtp.parse(raw).templates
  row = [x for x in parsed if x.name.lower().startswith("table row profession")][0]
  for arg in row.arguments:
    if arg.name == 'materials':
      obj[arg.name] = [{'quantity': int(x[0].strip('x')), 'item': strip_itemlink(x[1]).strip()} for x in [x.strip().split(' ',1) for x in arg.value.split(",")]]
    elif arg.name.startswith('tier') and arg.value.strip() != '':
      x = arg.value.strip().split(' ',1)
      obj[arg.name] = {'quantity': int(x[0].strip('x')), 'item': strip_itemlink(x[1]).strip()}
    elif arg.name == 'link':
      obj['profession'] = arg.value.split('/')[0].strip()
    else:
      obj[arg.name] = arg.value.strip()
  return obj

def parse_item_tooltip(raw):
  obj = {'type': 'item'}
  parsed = wtp.parse(raw).templates[0]
  for arg in parsed.arguments:
    if arg.name.strip() == 'value':
      obj[arg.name.strip()] = arg.value.replace("{{copper}}","").strip()
    elif arg.name.strip() == '1':
      continue
    else:
      obj[arg.name.strip()] = arg.value.strip()
  return obj

@cli.command()
@click.option('--output_file', default="professions.jsonl", help='destination to save recipes to.')
def update_recipes(output_file):
  """Fetches recipes from the neverwinter wiki"""
  site = mwclient.Site('neverwinter.gamepedia.com', path="/")
  with open(output_file, 'w') as out:
    for page in tqdm(PROFESSIONS, desc="Fetching Professions", unit=" professions"):
      profession = site.pages[page]
      recipes = [x for x in profession.links() if f"{profession.name}/" in x.name]
      for recipe in tqdm(recipes, desc=f"Fetching recipes for {profession.name}", unit=" recipes"):
        r = parse_profession_row(recipe.text())
        out.write(json.dumps(r))
        out.write('\n')

@cli.command()
@click.option('--output_file', default="data.jsonl", help='destination to save items to.')
def update_items(output_file):
  """fetches profession related materials and items from the neverwinter wiki"""
  site = mwclient.Site('neverwinter.gamepedia.com', path="/")
  with open(output_file, 'w') as out:
    for profession in PROFESSIONS:
      for item in tqdm(site.pages[profession].templates(), desc=f"Fetching items related to {profession}", unit=" items"):
        if item.name.endswith(f"/Tooltip"):
          obj = parse_item_tooltip(item.text())
        elif item.name.startswith(f"{profession}/"):
          obj = parse_profession_row(item.text())
        else:
          continue
        out.write(json.dumps(obj))
        out.write('\n')

if __name__ == '__main__':
    cli()
