# coding: utf-8

"""
List of classes aiming to extract information from a history OSM data file
"""

# if sys.version_info[0] == 3:
#     from datetime import timezone
from datetime import datetime

import pandas as pd
import osmium as osm


#####

DEFAULT_START = pd.Timestamp("2000-01-01T00:00:00Z")

#####

class TagGenomeHandler(osm.SimpleHandler):

    def __init__(self):
        osm.SimpleHandler.__init__(self)
        self.taggenome = []

    def tag_inventory(self, elem, elem_type):
        for tag in elem.tags:
            self.taggenome.append([elem_type,
                                   elem.id,
                                   elem.version,
                                   tag.k,
                                   tag.v])

    def node(self, n):
        self.tag_inventory(n, "node")

    def way(self, w):
        self.tag_inventory(w, "way")

    def relation(self, r):
        self.tag_inventory(r, "relation")

#####
        
class TimelineHandler(osm.SimpleHandler):
    """Encapsulates the recovery of elements inside the OSM history.

    This history is composed of nodes, ways and relations, that have
    common attributes (id, version, visible, timestamp, userid,
    changesetid, nbtags, tagkeys). Nodes are characterized with their
    latitude and longitude; ways with the nodes that composed them;
    relations with a list of OSM elements that compose it, aka their
    members (a member can be a node, a way or another relation). We
    gather these informations into a single attributes named
    'descr'. The timeline handler consider the OSM element type as
    well (node, way or relation). OSM history dumps do not seem to
    update properly 'visible' flag of OSM elements, so this handler
    recode it according to elements property.

    """
    def __init__(self):
        """ Class default constructor"""
        osm.SimpleHandler.__init__(self)
        self.elemtimeline = [] # Dictionnary of OSM elements
        print("Initialization of a TimelineHandler instance !")
        
    def node(self,n):
        """
        Node recovery: each record in the history is saved as a row in the
        element dataframe.
        
        The features are the following: id, version, visible?,
        timestamp, userid, chgsetid, nbtags, tagkeys, elem type
        ("node") and geographical coordinates (lat, lon)

        """
#        print("n")
        nodeloc = n.location
        # If the location is not valid, then the node is no longer available
        if nodeloc.valid():
            self.elemtimeline.append([n.id,
                                      n.version,
                                      True, # 'visible' flag not OK
                                      pd.Timestamp(n.timestamp),
                                      n.uid,
                                      n.changeset,
                                      len(n.tags),
                                      [x.k for x in n.tags],
                                      "node",
                                      (nodeloc.lat, nodeloc.lon)])
        else:
            self.elemtimeline.append([n.id,
                                      n.version,
                                      False,
                                      pd.Timestamp(n.timestamp),
                                      n.uid,
                                      n.changeset,
                                      len(n.tags),
                                      [x.k for x in n.tags],
                                      "node",
                                      (float('nan'), float('nan'))])


    def way(self,w):
        """
        Way recovery: each record in the history is saved as a row in the
        element dataframe.

        The features are the following: id,
        version, visible?, timestamp, userid, chgsetid, nbtags,
        tagkeys, elem type ("way") and a tuple (node quantity, list of
        nodes)
        """
#        print("w")
        # If there is no nodes in the way, then the way is no longer available
        if len(w.nodes) > 0 :
            self.elemtimeline.append([w.id,
                                      w.version,
                                      True, # 'visible' flag not OK
                                      pd.Timestamp(w.timestamp),
                                      w.uid,
                                      w.changeset,
                                      len(w.tags),
                                      [x.k for x in w.tags],
                                      "way",
                                      (len(w.nodes), [n.ref for n in w.nodes])])
        else:
            self.elemtimeline.append([w.id,
                                      w.version,
                                      False,
                                      pd.Timestamp(w.timestamp),
                                      w.uid,
                                      w.changeset,
                                      len(w.tags),
                                      [x.k for x in w.tags],
                                      "way",
                                      (len(w.nodes), [n.ref for n in w.nodes])])

                                     
    def relation(self,r):
        """
        Relation recovery: each record in the history is saved as a row in
        the element dataframe.

        The features are the following: id,
        version, visible?, timestamp, userid, chgsetid, nbtags,
        tagkeys, elem type ("relation") and a tuple (member quantity,
        list of members under format (id, role, type))
        """
        # print("r")
        # If the relation does not include any member, it is no longer available
        if len(r.members) > 0 or len(r.tags) > 0 :
            self.elemtimeline.append([r.id,
                                      r.version,
                                      True, # 'visible' flag not OK
                                      pd.Timestamp(r.timestamp),
                                      r.uid,
                                      r.changeset,
                                      len(r.tags),
                                      [x.k for x in r.tags],
                                      "relation",
                                      (len(r.members), [(m.ref,m.role,m.type)
                                                        for m in r.members])])
        else:
            self.elemtimeline.append([r.id,
                                      r.version,
                                      False,
                                      pd.Timestamp(r.timestamp),
                                      r.uid,
                                      r.changeset,
                                      len(r.tags),
                                      [x.k for x in r.tags],
                                      "relation",
                                      (len(r.members), [(m.ref,m.role,m.type)
                                                        for m in r.members])])

