#
# MTGO ToolBox
#
# - Currently support parsing xml cards/sets from MTGO and populate
#   a DB for faster access. Parsing the XML files everytime is time
#   consuming
#
# TBD and Research:
#   - Delta DB update
#   - support Image support (gatherer)
#
# Cool project:
#   - Image recognition (OCR or pHash)
#   - fuzzy search (console for mtgo)
#
# Schemas (simple example and may be not complete)
#
# ID1040_XXXX : Cardname string ID
#
# <CardSet>
#     <DigitalObject>
#        <CARDNAME_STRING id='ID1040_14132'/>
#        <CARDNAME_TOKEN id='ID1041_14114'/>
#        <CARDSETNAME_STRING id='ID1043_4'/>
#        <REAL_ORACLETEXT_STRING id='ID1165_12833'/>
#        <CARDTEXTURE_NUMBER value='2000420'/>
#        <UNTRADABLE value='1'/>
#        <IS_DIGITALOBJECT/>
#         <IS_CONTAINER/>
#        <IS_TROPHY/>
#         <IS_BOOSTER/>
#         <UNTRADABLE/>
#    </DigitalObject>
# </CardSet>
# ..
# <CARDNAME_STRING_ITEMS>
# <CARDNAME_STRING_ITEM id='ID1040_1'>Swamp</CARDNAME_STRING_ITEM>
# ...
# </CARDNAME_STRING_ITEMS>
#
path_to_data = '/cygdrive/f/Users/michel/AppData/Local/Apps/2.0/Data/CEK952Z0.L1H/NN8TA4NR.1Y1/mtgo..tion_1ad988e60282d0d8_0003.0004_179e647611f24e5a/Data/CardDataSource/'

path_to_data = '/cygdrive/c/Users/michel/AppData/Local/Apps/2.0/Data/CEK952Z0.L1H/NN8TA4NR.1Y1/mtgo..tion_1ad988e60282d0d8_0003.0004_092c585102b108da/Data/CardDataSource/'

fname_CARDSETNAME_STRING = 'CARDSETNAME_STRING.xml'
fname_CARDNAME_STRING = 'CARDNAME_STRING.xml'
fname_client_GTC = 'client_GTC.xml'

import os,sys
import string
import json
import re
import time
from xml.parsers import expat
import sqlite3

#
# Globals
#
global gSetDict
gSetDict = {}

class Element:
    'A parsed XML element'
    def __init__(self,name,attributes):
        'Element constructor'
        # The element's tag name
        self.name = name
        # The element's attribute dictionary
        self.attributes = attributes
        # The element's cdata
        self.cdata = ''
        # The element's child element list (sequence)
        self.children = []

    def AddChild(self,element):
        'Add a reference to a child element'
        self.children.append(element)

    def getAttribute(self,key):
        'Get an attribute value'
        return self.attributes.get(key)

    def getData(self):
        'Get the cdata'
        return self.cdata

    def getElements(self,name=''):
        'Get a list of child elements'
        #If no tag name is specified, return the all children
        if not name:
            return self.children
        else:
            # else return only those children with a matching tag name
            elements = []
            for element in self.children:
                if element.name == name:
                    elements.append(element)
            return elements
gCount = 0
class Xml2Obj:
    'XML to Object'
    def __init__(self):
        self.root = None
        self.nodeStack = []

    def StartElement(self,name,attributes):
        'SAX start element even handler'
        # Instantiate an Element object
        element = Element(name.encode(),attributes)
        # Push element onto the stack and make it a child of parent
        if len(self.nodeStack) > 0:
            parent = self.nodeStack[-1]
            parent.AddChild(element)
        else:
            self.root = element
        self.nodeStack.append(element)

    def EndElement(self,name):
        'SAX end element event handler'
        self.nodeStack = self.nodeStack[:-1]

    def CharacterData(self,data):
        'SAX character data event handler'
        if string.strip(data):
            # Got into problems with AEtherize first *TBD*
            try:
                edata = data.encode()
            except:
                # Todo: Either try to fix how unique is managed (keep unicode data)
                #         Best effort to encode('ascii'). Change code bellow to
                #         Character lookup. Fallback to ? for unknown character ?
                #
                for pos in range(0,len(data)):
                    if data[pos] == unicode(u'\xc6'):
                        data = data[0:pos] + 'AE'+data[pos+1:]
                    elif data[pos] == unicode(u'\xe9'):
                        data = data[0:pos] + 'E'+data[pos+1:]
                    elif data[pos] == unicode(u'\xfa'):
                        data = data[0:pos] + 'U'+data[pos+1:]
                    elif data[pos] == unicode(u'\xfb'):
                        data = data[0:pos] + 'U'+data[pos+1:]
                    elif data[pos] == unicode(u'\xe1'):
                        data = data[0:pos] + 'A'+data[pos+1:]
                    elif data[pos] == unicode(u'\xed'):
                        data = data[0:pos] + 'I'+data[pos+1:]
                    elif data[pos] == unicode(u'\xe2'):
                        data = data[0:pos] + 'A'+data[pos+1:]
                    elif data[pos] == unicode(u'\xe0'):
                        data = data[0:pos] + 'A'+data[pos+1:]
                edata = data.encode()
                data = edata
            element = self.nodeStack[-1]
            element.cdata += data
            return

    def Parse(self,filename):
        # Create a SAX parser
        Parser = expat.ParserCreate()

        # SAX event handlers
        Parser.StartElementHandler = self.StartElement
        Parser.EndElementHandler = self.EndElement
        Parser.CharacterDataHandler = self.CharacterData

        # Parse the XML File
        ParserStatus = Parser.Parse(open(filename,'r').read(), 1)

        return self.root

#
# Process XML files
#
count = 0
def print_tree( ptr ):
    global count
    global gElement
    print count, ptr.name,
    count += 1
    print ptr.attributes
    print ptr.getData()
    list = ptr.getElements()
    for elt in list:
        print_tree(elt)
#
# Build CARDNAME_STRING Dictionary
#
gCardId = {}
gCardName = {}
def build_cardname_dict( ptr ):
    list = ptr.getElements()
    # Add each element to the dictionary
    global gCardId
    global gCardName
    for elt in list:
        gCardId[ elt.attributes['id'] ] = elt.getData()
        gCardName[ elt.getData() ] = elt.attributes['id']
#
# Build Clone Card Name Dictionary
# and _patch_ CardDOCID card (add CNS and CNSID)
#
gCloneCardName = {}
def build_clone_cardname_dict():

    print '*** Patching CLONED entries ***'
    global gCloneDict
    for docid in gCloneDict.keys():

        # Card being Cloned (e.g. Original Card )
        clnid = gCloneDict [ docid ][ 'clnid' ]

        # Try to fill the fields set to NULL from the Card being Cloned
        # Loop as long as w/ found a CLONEID reference
        while clnid:
            for field in gCardDOCID[ docid ]:
                if gCardDOCID[ docid ][ field ] == None:
                    try:
                        gCardDOCID[ docid ][ field ] = gCardDOCID[ clnid ][ field ]
                    except:
                        raise RuntimeError("Clone Card "+clnid +" not found (Missing SET ?)")
            # Proceed to the next CLONED card reference if any
            clnid = gCardDOCID[ clnid ][ 'clnid' ]

        # Build a Dictionary to keep track of the Cards which are Cloned
        cns = gCardDOCID[ docid ][ 'cns' ]
        if cns not in gCloneCardName.keys():
            gCloneCardName[ cns ] = [ docid ]
        else:
            gCloneCardName[ cns ].append( docid )


#
# Write all dictionary to disk
#
def write_all_dict_to_disk():

    print '*** Writing all Dictionaries to Disk ***'
    with open('Dicts/cardid_dict.json', 'w') as configfile:
            json.dump(gCardId, configfile, indent=2)

    with open('Dicts/cardname_dict.json', 'w') as configfile:
            json.dump(gCardName, configfile, indent=2)

    with open('Dicts/docid_dict.json', 'w') as configfile:
            json.dump(gCardDOCID, configfile, indent=2)

    with open('Dicts/docidbyname_dict.json', 'w') as configfile:
            json.dump(gCardDOCIDbyName, configfile, indent=2)

    with open('Dicts/clone_dict.json', 'w') as configfile:
            json.dump(gCloneDict, configfile, indent=2)

    with open('Dicts/clonename_dict.json', 'w') as configfile:
            json.dump(gCloneCardName, configfile, indent=2)


#
# Read all dictionary to disk
#
def read_all_dict_from_disk():

    print '*** Reading all Dictionaries from Disk ***'
    global gCardID
    with open('Dicts/cardid_dict.json', 'r') as configfile:
            gCardID = json.load(configfile)

    global gCardName
    with open('Dicts/cardname_dict.json', 'r') as configfile:
            gCardName = json.load(configfile)

    global gCardDOCID
    with open('Dicts/docid_dict.json', 'r') as configfile:
            gCardDOCID = json.load(configfile)

    global gCardDOCIDbyName
    with open('Dicts/docidbyname_dict.json', 'r') as configfile:
            gCardDOCIDbyName = json.load(configfile)

    global gCloneDict
    with open('Dicts/clone_dict.json', 'r') as configfile:
            gCloneDict = json.load(configfile)

    global gCloneCardName
    with open('Dicts/clonename_dict.json', 'r') as configfile:
            gCloneCardName = json.load(configfile)


#
# Build CARDSETNAME_STRING Dictionary
#
gCardSetId = {}
gCardSetName = {}
def build_cardsetname_dict( ptr ):
    list = ptr.getElements()
    # Add each element to the dictionary
    global gCardSetId
    global gCardSetName
    for elt in list:
        gCardSetId[ elt.attributes['id'] ] = elt.getData()
        gCardSetName[ elt.getData() ] = elt.attributes['id']


gCardDOCID = {}
gCardDOCIDbyName = {}
gCloneDict = {}

def dump_docid( docid, entry ):

    print 40*'-'
    print 'DOCID:', docid
    for field in entry.keys():
        print field,':', entry[ field ]
    print 40*'-'

#
# build_set
#
# Fill gCardDOCID, gCardDOCIDbyName and gCloneDict
#
def build_set( ptr ):
    list = ptr.getElements()
    global gCardDOCID
    for elt in list:
        # print elt.attributes[ 'DigitalObjectCatalogID' ]
        data = elt.getData()    # expected to be Null

        # Supported Fields
        CIS = None                    # COLLECTOR_INFO_STRING
        CNS = None                    # CARDNAME_STRING
        CNSID = None                # ...
        CSNS = None
        CSNSID = None
        CLNID = None
        ISFOIL = None
        ISLAND = None
        ISCREATURE = None
        ISARTIFACT = None
        ISEQUIPMENT = None
        ISCURSE = None
        ISENCHANTMENT = None
        ISLOCALENCHANTMENT = None
        ISFLYING = None
        ISFIRSTSTRIKE = None
        RARITY = None
        ISPROMO = None
        POWER = None
        TOUGHNESS = None
        COLOR = None

        for field in elt.getElements():
            # print field.name, field.attributes, '#', field.getData(), '#'
            if field.name == "COLLECTOR_INFO_STRING":
                    try:
                        CIS = field.attributes['value']
                    except:
                        CIS = None
            if field.name == "CARDNAME_STRING":
                    CNS   = gCardId[ field.attributes['id'] ]
                    CNSID = field.attributes['id']
            if field.name == "CARDSETNAME_STRING":
                    CSNSID = field.attributes['id']
                    CSNS   = gCardSetId[ CSNSID ]
            if field.name == "CLONE_ID":
                    CLNID  = field.attributes['value']
            if field.name == "IS_FOIL":
                    ISFOIL = True
            if field.name == "IS_LAND":
                    ISLAND = True
            if field.name == "IS_CREATURE":
                    ISCREATURE = True
            if field.name == "IS_ARTIFACT":
                    ISARTIFACT = True
            if field.name == "IS_EQUIPMENT":
                    ISEQUIPMENT = True
            if field.name == "IS_CURSE":
                    ISCURSE = True
            if field.name == "IS_ENCHANTMENT":
                ISENCHANTMENT = True
            if field.name == "IS_LOCAL_ENCHANTMENT":
                ISLOCALENCHANTMENT = True
            if field.name == "FLYING":
                    ISFLYING = True
            if field.name == "FIRST_STRIKE":
                    ISFIRSTSTRIKE = True
            if field.name == "RARITY_STATUS":
                    RARITY = field.attributes['id']
            if field.name == "IS_PROMO":
                    try:
                        ISPROMO = field.attributes['value']
                    except:
                        # <ISPROMO/>
                        pass
            if field.name == 'COLOR':
                    COLOR = field.attributes['id']
            if field.name == 'POWER':
                    POWER = field.attributes['value']
            if field.name == 'TOUGHNESS':
                    TOUGHNESS = field.attributes['value']

        # Check if DOCID already present in DOCID Dictionary
        # Skip this test as it slows down thing considerably
        #        if elt.attributes[ 'DigitalObjectCatalogID' ] in gCardDOCID.keys():
        #        if elt. attributes[ 'DigitalObjectCatalogID' ] in prevKeys:
        #            raise RuntimeError("DOCID "+elt.attributes[ 'DigitalObjectCatalogID' ]+"already present in DOCID Dictionary")
        gCardDOCID[ elt.attributes[ 'DigitalObjectCatalogID' ] ] = { 'cis' : CIS, 'cns': CNS, 'cnsid' : CNSID,
                                                                     'csns' : CSNS, 'csnsid' : CSNSID,
                                                                     'isfoil' : ISFOIL, 'island' : ISLAND,
                                                                     'iscreature' : ISCREATURE, 'isequip' : ISEQUIPMENT,
                                                                     'isartifact' : ISARTIFACT, 'iscurse' : ISCURSE,
                                                                     'isenchant'  : ISENCHANTMENT, 'islocalenchant' : ISLOCALENCHANTMENT,
                                                                     'isflying'   : ISFLYING, 'isfirststrike' : ISFIRSTSTRIKE,
                                                                     'rarity'     : RARITY, 'ispromo' : ISPROMO,
                                                                     'color'       : COLOR, 'power' : POWER, 'toughness' : TOUGHNESS,
                                                                     'clnid'      : CLNID }
        #
        # Helper Build NameID to List of Card
        # Collision happens so far only for Booster - so skip check for now
        #if CNSID:
        #        if CNSID in gCardDOCIDbyName.keys():
        #        gCardDOCIDbyName[ CNSID ].append( [ elt.attributes[ 'DigitalObjectCatalogID' ], CNS, CIS, CSNS, CSNSID ] )
        #    else:
        gCardDOCIDbyName[ CNSID ] = [ elt.attributes[ 'DigitalObjectCatalogID' ], CNS, CIS, CSNS, CSNSID ]
        #
        # Store CLONE_ID Card to expand them later
        #
        if not CNS:
            if CLNID:
                # Fields available for Clone Entries
                gCloneDict[ elt.attributes[ 'DigitalObjectCatalogID' ] ] = { 'clnid': CLNID,
                    'csns': CSNS, 'csnsid': CSNSID,        # CARDSETNAME_STRING and ID
                    'cis': CIS,
                    'rarity': RARITY,
                    'ispromo' : ISPROMO,
                    'isfoil' : ISFOIL }


# Process XML File to Data Tree
#
def parse_file( aFilename ):

    parser = Xml2Obj()
    return parser.Parse( aFilename )

def read_dekfile( aFilename ):

    parser = Xml2Obj()
    return parser.Parse( aFilename )

def parse_dekfile( ptr ):

    deck_dict = {}
    list = ptr.getElements()
    for elt in list:

        if elt.name == 'Cards':
            print gCardDOCID[ 'DOC_'+elt.attributes['CatID'] ], elt.attributes['Quantity'], elt.attributes['Sideboard']

def parse_mwDeck( aFilename ):

    # Read deck file
    f = open( aFilename )
    d = f.read()
    d = d.split('\n')
    f.close()

    lDeck = {}
    # Parse each line
    for line in d:
        if not line:
            continue
        sideboard = False
        if line[:2] == '//':
            continue
        if line[:2] == 'SB':
            sideboard = True
            line = line[3:]
        # Switch to re
        str_re0 = " *([0-9]+) *\[(.*)\] *(.*) *"
        m = re.search( str_re0, line )
        lQuantity = m.group(1)
        lSet = m.group(2)
        lName = m.group(3)
        # dbg print lQuantity, lName, lSet, sideboard
        # Fix Name
        lName = lName.replace("'","\\'")
        lDeck[gCardName[ lName ]] = { 'q' : lQuantity, 's' : lSet, 'n' : lName,'sb' : sideboard }
    return lDeck
#
# MTGO Deck (Local) Management
#
mtgo_deck_header = """<?xml version="1.0" encoding="utf-8"?>
<Deck xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <NetDeckID>0</NetDeckID>
  <PreconstructedDeckID>0</PreconstructedDeckID>
"""
mtgo_deck_line = """  <Cards CatID="%s" Quantity="%s" Sideboard="%s" Name="" Row="%d" Col="%d" />"""
mtgo_deck_footer = """</Deck>"""

#
# write_local_mtgo_deck( aDeck )
#   - write a .dek file corresponding to the cards provided with aDeck
#
# Format:
#<?xml version="1.0" encoding="utf-8"?>
#<Deck xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
#      xmlns:xsd="http://www.w3.org/2001/XMLSchema">
#  <NetDeckID>0</NetDeckID>
#  <PreconstructedDeckID>0</PreconstructedDeckID>
#  <Cards CatID="42708" Quantity="3" Sideboard="0" Name="" Row="0" Col="0" />
#   ...
#  <Cards CatID="45410" Quantity="5" Sideboard="0" Name="" Row="0" Col="0" />
#</Deck>
#
# TBD: Row/Col attributes are currently set to 0
#      Check purpose and how to set if required
#
def write_local_mtgo_deck( aDeck ):

    f = open("mtgo_deck_default.dek", 'w')
    f.write( mtgo_deck_header )
    for entry in aDeck.keys():
        try:
            f.write( mtgo_deck_line % ( entry[4:], aDeck[ entry ]['deck_quantity'], repr(aDeck[entry]['sb_quantity']).lower(), 0, 0 )    )
            f.write('\n')
        except:
            print 'Card not found:', entry, aDeck[ entry ]
    f.write( mtgo_deck_footer )
    f.close()


#
# def misc. tests
#
def misc_test():
    print gCardDOCID[ 'DOC_5' ]
    print gCardDOCID[ 'DOC_46497']
    deck = read_dekfile( 'CSTD_WGR_HUNT_REv1.dek' )
    parse_dekfile( deck )


def lookup_card_by_name( aName ):

    # Lookup card by name
    cid = gCardName[ aName ]

    # Lookup CloneCardName
    cidl = None
    try:
        cidl = gCloneCardName[ aName ]
    except:
        print '*** INFO *** : No clone card found for:', aName

    if cidl:
        return [ cid, ] + cidl
    else:
        return [ cid, ]

#
# Build Dictionaries
#
def build_main_dictionaries():

    global path_to_data

    # Path to Card Sets data
    if len(sys.argv) > 1:
        path_to_data = sys.argv[1]

    print '*** Processing SETS ***'
    t0 = time.time()
    # List and BUILD MTG Set (e.g. client_*.xml)
    fileList = os.listdir( path_to_data )
    for f in fileList:
        lName = None
        lNameDO = None
        try:
            if f[:len('client_')] == 'client_' and f[-len('.xml'):] == '.xml':
                lName = f
            if f[:len('client_')] == 'client_' and f[-len('_DO.xml'):] == '_DO.xml':
                lNameDO = f
        except:
            pass
        lSetName = None
        if lName or lNameDO:
            lSetName = f[len('client_'):len(f)-len('.xml')]

        # Skip DO files
        if lName:
            print lSetName,
            element = parse_file( path_to_data + lName )
            gSetDict[ lSetName ] = element
            build_set( element )
    print '\n*** Done processing SETS ***'

    # Build clonecard name dictionary
    # _patch_ docid card dictionary for clone card
    build_clone_cardname_dict()
    t1 = time.time()
    print t1-t0

    # Write all Dictionaries to Disk
    write_all_dict_to_disk()

#
# Update DB
#
# TBD: Add Index support if available
#
def create_update_DB():

    print '*** Create/Update DB ***'
    conn = sqlite3.connect('Dicts/mtgo.db')
    c    = conn.cursor()

    try:
        drop_table_str = '''DROP TABLE cards'''
        c.execute( drop_table_str )
    except:
        pass

    # Fields to use for Create TABLE
    field_list = [ 'docid' ]
    for field in gCardDOCID[ gCardDOCID.keys()[ 0 ] ]:
        field_list.append( field )

    fields_str = '( '
    first = True
    str  = ''' "%s" '''
    str2 = ''' '%s' '''
    values_str  = "INSERT INTO cards VALUES( "
    values_str2 = "INSERT INTO cards VALUES( "
    for field in field_list:
        if first:
            fields_str = fields_str + field + ' text'
            values_str  = values_str + str
            values_str2 = values_str2 + str2
            first = False
        else:
            fields_str = fields_str + ', ' + field + ' text'
            values_str  = values_str  + ', ' + str
            values_str2 = values_str2 + ', ' + str2

    values_str  = values_str + ' )'
    values_str2 = values_str2 + ' )'
    fields_str = fields_str + ' )'

    create_table_str = '''CREATE TABLE cards %s ''' % fields_str
    c.execute( create_table_str )

    insert_table_str = values_str
    insert_table_str2 = values_str2

    for e in gCardDOCID:
        name = gCardDOCID[ e ][ 'cns' ]
        # xxx/MR: Ugly hack to work around ' and " in name
        if name and name.find( '"') != -1:
            exec_str = insert_table_str2 % tuple( [ e ] + gCardDOCID[ e ].values() )
        else:
            try:
                exec_str = insert_table_str % tuple( [ e ] + gCardDOCID[ e ].values() )
            except:
                print insert_table_str
                print gCardDOCID[ e ].values()
        c.execute( exec_str )

    conn.commit()
    conn.close()


#
# Fetch card info from DB
#
# TBD: CSTD is not current anymore
#
def db_lookup_card_by_name( aName, cstd = False ):

    conn = sqlite3.connect('Dicts/mtgo.db')
    c    = conn.cursor()

    # xxx/MR: Fetching the schema should be done only once and store globally
    select_str = """SELECT sql from sqlite_master where name == 'cards' ; """
    c.execute( select_str )
    row = c.fetchone()
    fields_str  = row[0].split('(')[1].replace(' text,', ',')[:-7].replace(' ','"').replace(',','",')+'"'
    fields_list = eval( "["+fields_str+"]" )

    select_str = """SELECT * from cards where cns like "%%%s%%" ;""" % aName.replace("'","\\'")
    # Current Standard query
    if cstd:
        select_str = """select * from cards where csns in ( 'RTR', 'M13', 'M14', 'ISD', 'DKA', 'AVR', 'GTC' ) and isfoil != 'True' and cns like "%%%s%%" ;""" % aName.replace("'","\\'")

    c.execute( select_str )

    card_dict = {}

    for row in c.fetchall():
            # xxx/MR: Assert if fields_list[0] != from docid
            if fields_list[0] != 'docid':
                raise RuntimeError("docid field expected")
            docid = row[0]
            idx = 1
            for field in fields_list[1:]:
                if idx == 1:
                    card_dict[ docid ] = {}
                card_dict[ docid ][ field ] = row[ idx ]
                idx = idx + 1

    conn.close()

    return card_dict


#
# MAIN()
#
if __name__ == '__main__':

    # Default Settings
    cmd_bmd = False
    cmd_rad = False
    cmd_cdb = False
    cmd_bcd = False

    # Parse CARDNAME_STRING
    if cmd_bcd:
        filename = path_to_data + fname_CARDNAME_STRING
        print 'Processing:', filename.split('/')[-1]
        element = parse_file( filename )

    # Build CARDNAME Dictionary
    if cmd_bcd:
        build_cardname_dict( element )

    # Build CARDSETNAME Dictionary
    if cmd_bcd:
        filename = path_to_data + fname_CARDSETNAME_STRING
        print 'Processing:', filename.split('/')[-1]
        element = parse_file( filename )
        build_cardsetname_dict( element )

    # Build Main Dictionaries
    if cmd_bmd:
        build_main_dictionaries()

    # Process mwDeck
    #lDeck = parse_mwDeck( "deck225309.mwDeck" )
    #write_local_mtgo_deck( lDeck )

    # Read all Dictionaries
    if cmd_rad:
        read_all_dict_from_disk()

    # Create Update DB
    if cmd_cdb:
        create_update_DB()

#    print '*** lookup card by name ***'
#    results = db_lookup_card_by_name( "Balustrade" )
#    dump_docid( results.keys()[0], results[ results.keys()[0] ] )

    # Lookup card
    # cid = lookup_card_by_name( "Tragic Slip" )
    # print cid
    # print gCardId[ cid[0] ], gCardDOCIDbyName[ cid[0] ]

    #
    # Simple DEK format:
    #   All main deck cards are first listed then sideboard card.
    #   An empty line separate the main deck list from the sideboard
    #
    f = open('simple.dek')
    d = f.read()
    d = d.split('\n')
    f.close()

    # xxx/MR: TBD - Fix case where same card is in main deck and side board. Currently sideboard entry
    #                overwrite the main entry.
    deck = {}
    sb = False
    for e in d:
        if e:
            idx = e.find(' ')
            q = e[:idx]
            n = e[idx:].strip()

            results = db_lookup_card_by_name( n, cstd = True )
            key = results.keys()[0]

            if not key in deck.keys():
                card = results[key]
                card['deck_quantity'] = 0
                card['sb_quantity']   = 0
            else:
                card = deck[ key ]

            if not sb:
                card['deck_quantity'] = q
            else:
                card['sb_quantity'] = q

            if not key in deck.keys():
                deck[ key ] = card
            else:
                # Card already present in deck
                # We assume we are processing sideboard card
                # If not throw an error - we do not support the same cards
                # being set twice in the maindeck section.
                if not sb:
                    raise RuntimeError("Card already in deck and not being sideboarded")
                deck[ key ]['sb_quantity'] = q
            print q,'"'+n+'"', key, sb
        else:
            # Found an empty line - assume we start the sideboard part
            sb = True

    write_local_mtgo_deck( deck )
