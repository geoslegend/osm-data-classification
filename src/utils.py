# !/usr/bin/env python
# coding: utf-8

"""
Some utility functions aiming to analyse OSM data
"""

import datetime as dt
import pandas as pd
import numpy as np
from datetime import timedelta
import re

### OSM data exploration ######################
def updatedelem(data):
    """Return an updated version of OSM elements

    Parameters
    ----------
    data: df
        OSM element timeline
    
    """
    updata = data.groupby(['elem','id'])['version'].max().reset_index()
    return pd.merge(updata, data, on=['id','version'])

def datedelems(history, date):
    """Return an updated version of history data at date

    Parameters
    ----------
    history: df
        OSM history dataframe
    date: datetime
        date in datetime format

    """
    datedelems = (history.query("ts <= @date")
                  .groupby(['elem','id'])['version']
                  .max()
                  .reset_index())
    return pd.merge(datedelems, history, on=['elem','id','version'])

def osm_stats(osm_history, timestamp):
    """Compute some simple statistics about OSM elements (number of nodes,
    ways, relations, number of active contributors, number of change sets

    Parameters
    ----------
    osm_history: df
        OSM element up-to-date at timestamp
    timestamp: datetime
        date at which OSM elements are evaluated
    """
    osmdata = datedelems(osm_history, timestamp)    
#    nb_nodes, nb_ways, nb_relations = list(osm_data.elem.value_counts())
    nb_nodes = len(osmdata.query('elem=="node"'))
    nb_ways = len(osmdata.query('elem=="way"'))
    nb_relations = len(osmdata.query('elem=="relation"'))
    nb_users = osmdata.uid.nunique()
    nb_chgsets = osmdata.chgset.nunique()
    return [nb_nodes, nb_ways, nb_relations, nb_users, nb_chgsets]    

def osm_chronology(history, start_date, end_date=dt.datetime.now()):
    """Evaluate the chronological evolution of OSM element numbers

    Parameters
    ----------
    history: df
        OSM element timeline
    
    """
    timerange = pd.date_range(start_date, end_date, freq="1M").values 
    osmstats = [osm_stats(history, str(date)) for date in timerange]
    osmstats = pd.DataFrame(osmstats, index=timerange,
                            columns=['n_nodes', 'n_ways', 'n_relations',
                                     'n_users', 'n_chgsets'])
    return osmstats

### OSM metadata extraction ####################
def group_count(metadata, data, grp_feat, res_feat, namesuffix):
    """Group-by 'data' by 'grp_feat' and element type features, count element
    corresponding to each grp_feat-elemtype tuples and merge them into metadata
    table

    Parameters
    ----------
    metadata: df
        Dataframe that will integrate the new features
    data: df
        Dataframe from where information is grouped
    grp_feat: object
        string that indicates which feature from 'data' must be used to group items
    res_feat: object
        string that indicates the measured feature (how many items correspond
    to the criterion)
    namesuffix: object
        string that ends the new feature name
    
    """
    md_ext = (data.groupby([grp_feat, 'elem'])[res_feat]
              .count()
              .unstack()
              .reset_index()
              .fillna(0))
    md_ext['elem'] = md_ext[['node','relation','way']].apply(sum, axis=1)
    md_ext = md_ext[[grp_feat, 'elem', 'node', 'way', 'relation']]
    colnames = "n_" + md_ext.columns.values[-4:] + namesuffix
    md_ext.columns = [grp_feat, *colnames]
    return pd.merge(metadata, md_ext, on=grp_feat, how='outer').fillna(0)

def group_nunique(metadata, data, grp_feat, res_feat, namesuffix):
    """Group-by 'data' by 'grp_feat' and element type features, count unique
    element corresponding to each grp_feat-elemtype tuples and merge them into
    metadata table

    Parameters
    ----------
    metadata: df
        Dataframe that will integrate the new features
    data: df
        Dataframe from where information is grouped
    grp_feat: object
        string that indicates which feature from 'data' must be used to group items
    res_feat: object
        string that indicates the measured feature (how many items correspond
    to the criterion)
    namesuffix: object
        string that ends the new feature name

    """
    md_ext = (data.groupby([grp_feat, 'elem'])[res_feat]
              .nunique()
              .unstack()
              .reset_index()
              .fillna(0))
    md_ext['elem'] = md_ext[['node','relation','way']].apply(sum, axis=1)
    md_ext = md_ext[[grp_feat, 'elem', 'node', 'way', 'relation']]
    colnames = "n_" + md_ext.columns.values[-4:] + namesuffix
    md_ext.columns = [grp_feat, *colnames]
    return pd.merge(metadata, md_ext, on=grp_feat, how='outer').fillna(0)


def group_stats(metadata, data, grp_feat, res_feat, nameprefix, namesuffix):
    """Group-by 'data' by 'grp_feat' and element type features, compute basic
    statistic features (min, median, max) corresponding to each
    grp_feat-elemtype tuples and merge them into metadata table

    Parameters
    ----------
    metadata: df
        Dataframe that will integrate the new features
    data: df
        Dataframe from where information is grouped
    grp_feat: object
        string that indicates which feature from 'data' must be used to group items
    res_feat: object
        string that indicates the measured feature (how many items correspond
    to the criterion)
    nameprefix: object
        string that begins the new feature name
    namesuffix: object
        string that ends the new feature name

    """
    md_ext = (data.groupby(grp_feat)[res_feat].agg({'min': "min",
                                                    'med': "median",
                                                    'max': "max"}).reset_index())
    # md_ext.med = md_ext.med.astype(int)
    md_ext = md_ext[[grp_feat, 'min', 'med', 'max']]
    colnames = [nameprefix + op + namesuffix for op in md_ext.columns.values[1:]]
    md_ext.columns = [grp_feat, *colnames]
    return pd.merge(metadata, md_ext, on=grp_feat, how='outer').fillna(0)

def init_metadata(osm_elements, init_feat, duration_feat='activity_d',
                  timeunit='day'):
    """ This function produces an init metadata table based on 'init_feature'
    in table 'osm_elements'. The intialization consider timestamp measurements
    (generated for each metadata tables, i.e. elements, change sets and users).

    Parameters
    ----------
    osm_elements: pd.DataFrame
        OSM history data
    init_feat: object
        metadata basic feature name in string format
    duration_feat: object
        metadata duration feature name in string format
    timeunit: object
        time unit in which 'duration_feature' will be expressed

    Return
    ------
    metadata: pd.DataFrame
    metadata table with following features:
    init_feature (int) -- initializing feature ID
    first_at (datetime) -- first timestamp
    last_at (datetime) -- last timestamp
    activity (int) -- activity (in 'timeunit' format)
    
    """
    metadata = (osm_elements.groupby(init_feat)['ts']
                .agg({'first_at':"min", 'last_at':"max"})
                .reset_index())
    metadata[duration_feat] = metadata.last_at - metadata.first_at
    if timeunit == 'second':
        metadata[duration_feat] = (metadata[duration_feat] /
                                   timedelta(seconds=1))
    if timeunit == 'minute':
        metadata[duration_feat] = (metadata[duration_feat] /
                                   timedelta(minutes=1))
    if timeunit == 'hour':
        metadata[duration_feat] = metadata[duration_feat] / timedelta(hours=1)
    if timeunit == 'day':
        metadata[duration_feat] = metadata[duration_feat] / timedelta(days=1)
    return metadata

def enrich_osm_elements(osm_elements):
    """Enrich OSM history data by computing additional features

    Parameters
    ----------
    osm_elements: pd.DataFrame
        OSM history data
    
    """
    # Extract information from first and last versions
    osmelem_first_version = (osm_elements
                             .groupby(['elem','id'])['version', 'uid']
                             .first()
                             .reset_index())
    osm_elements = pd.merge(osm_elements, osmelem_first_version,
                                on=['elem','id'])
    osm_elements.columns = ['elem', 'id', 'version', 'visible', 'ts',
                                'uid', 'chgset', 'ntags', 'tagkeys',
                                'vmin', 'first_uid']
    osmelem_last_version = (osm_elements
                             .groupby(['elem','id'])['version', 'uid',
                                                     'visible']
                             .last()
                             .reset_index())
    osm_elements = pd.merge(osm_elements, osmelem_last_version,
                                on=['elem','id'])
    osm_elements.columns = ['elem', 'id', 'version', 'visible', 'ts',
                            'uid', 'chgset', 'ntags', 'tagkeys', 'vmin',
                            'first_uid', 'vmax', 'last_uid', 'available']

    # New version-related features
    osm_elements['init'] = osm_elements.version == osm_elements.vmin
    osm_elements['up_to_date'] = osm_elements.version == osm_elements.vmax
    osm_elements = osm_elements.drop(['vmin'], axis=1)

    # Whether or not an element will be corrected in the last version
    osm_elements['willbe_corr'] = np.logical_and(osm_elements.id
                                                 .diff(-1)==0,
                                              osm_elements.uid
                                                 .diff(-1)!=0)        
    osm_elements['willbe_autocorr'] = np.logical_and(osm_elements.id
                                                     .diff(-1)==0,
                                                     osm_elements.uid
                                                     .diff(-1)==0)

    # Time before the next modification
    osm_elements['nextmodif_in'] = - osm_elements.ts.diff(-1)
    osm_elements.loc[osm_elements.up_to_date,['nextmodif_in']] = pd.NaT
    osm_elements.nextmodif_in = (osm_elements.nextmodif_in
                                 .astype('timedelta64[h]'))

    # Time before the next modification, if it is done by another user
    osm_elements['nextcorr_in'] = osm_elements.nextmodif_in
    osm_elements['nextcorr_in'] = (osm_elements.nextcorr_in
                                   .where(osm_elements.willbe_corr,
                                          other=pd.NaT))

    # Time before the next modification, if it is done by the same user
    osm_elements['nextauto_in'] = osm_elements.nextmodif_in
    osm_elements['nextauto_in'] = (osm_elements.nextauto_in
                                   .where(osm_elements.willbe_autocorr,
                                                   other=pd.NaT))

    return osm_elements
    
def extract_elem_metadata(osm_elements):
    """ Extract element metadata from OSM history data

    Parameters
    ----------
    osm_elements: pd.DataFrame
        OSM history data
    
    Return
    ------
    elem_md: pd.DataFrame
        Change set metadata with timestamp information, version-related features
    and number of unique change sets (resp. users)
    
    """
    elem_md = init_metadata(osm_elements, ['elem','id'], 'lifecycle_d')
    elem_md['version'] = (osm_elements.groupby(['elem','id'])['version']
                       .max()
                       .reset_index())['version']
    elem_md = pd.merge(elem_md, osm_elements[['elem','id','version','visible']],
                       on=['elem', 'id', 'version'])
    elem_md['n_chgset'] = (osm_elements.groupby(['elem', 'id'])['chgset']
                           .nunique()
                           .reset_index())['chgset']
    elem_md['n_user'] = (osm_elements.groupby(['elem', 'id'])['uid']
                         .nunique()
                         .reset_index())['uid']
    elem_md['n_autocorr'] = (osm_elements
                             .groupby(['elem','id'])['willbe_autocorr']
                             .sum()
                             .reset_index()['willbe_autocorr']
                             .astype('int'))
    elem_md['n_corr'] = (osm_elements
                             .groupby(['elem','id'])['willbe_corr']
                             .sum()
                             .reset_index()['willbe_corr']
                             .astype('int'))
    return elem_md

def extract_chgset_metadata(osm_elements):
    """ Extract change set metadata from OSM history data

    Parameters
    ----------
    osm_elements: pd.DataFrame
        OSM history data
    
    Return
    ------
    chgset_md: pd.DataFrame
        Change set metadata with timestamp information, user-related features
    and other features describing modification and OSM elements themselves
    
    """
    chgset_md = init_metadata(osm_elements, 'chgset', 'duration_m', 'minute')

    # User-related features
    chgset_md = pd.merge(chgset_md,
                         osm_elements[['chgset','uid']].drop_duplicates(),
                         on=['chgset'])
    chgset_md['user_lastchgset_h'] = (chgset_md.groupby('uid')['first_at']
                                      .diff())
    chgset_md.user_lastchgset_h = (chgset_md.user_lastchgset_h /
                                   timedelta(hours=1))

    # Modification-related features
    chgset_md = group_count(chgset_md, osm_elements, 'chgset', 'id', '_modif')
    osmmodif_cr = osm_elements.query("init")        
    chgset_md = group_count(chgset_md, osmmodif_cr, 'chgset', 'id', '_modif_cr')
    osmmodif_del = osm_elements.query("not init and not visible")
    chgset_md = group_count(chgset_md, osmmodif_del, 'chgset', 'id',
                            '_modif_del')
    osmmodif_imp = osm_elements.query("not init and visible")
    chgset_md = group_count(chgset_md, osmmodif_imp, 'chgset', 'id',
                            '_modif_imp')

    # Number of modifications per unique element
    contrib_byelem = (osm_elements.groupby(['elem', 'id', 'chgset'])['version']
                      .count()
                      .reset_index())
    chgset_md = group_stats(chgset_md, contrib_byelem, 'chgset', 'version',
                            'n', '_modif_byelem')

    # Element-related features
    chgset_md = group_nunique(chgset_md, osm_elements, 'chgset', 'id', '')        
    osmelem_cr = osm_elements.query("init and available")
    chgset_md = group_nunique(chgset_md, osmelem_cr, 'chgset', 'id', '_cr')
    osmelem_imp = osm_elements.query("not init and visible and available")
    chgset_md = group_nunique(chgset_md, osmelem_imp, 'chgset', 'id', '_imp')
    osmelem_del = osm_elements.query("not init and not visible and not available")
    chgset_md = group_nunique(chgset_md, osmelem_del, 'chgset', 'id', '_del')

    return chgset_md

def extract_user_metadata(osm_elements, chgset_md):
    """ Extract user metadata from OSM history data

    Parameters
    ----------
    osm_elements: pd.DataFrame
        OSM history data
    chgset_md: pd.DataFrame
        OSM change set metadata
    
    Return
    ------
    user_md: pd.DataFrame
        User metadata with timestamp information, changeset-related features
    and other features describing modification and OSM elements themselves
    
    """
    user_md = init_metadata(osm_elements, 'uid')

    # Change set-related features
    user_md['n_chgset'] = (osm_elements.groupby('uid')['chgset']
                           .nunique()
                           .reset_index())['chgset']
    user_md = group_stats(user_md, chgset_md, 'uid', 'user_lastchgset_h',
                          't', '_between_chgsets_h')
    user_md = group_stats(user_md, chgset_md, 'uid', 'duration_m',
                                    'd', '_chgset_insec')
    user_md = group_stats(user_md, chgset_md, 'uid', 'n_elem_modif',
                              'n', '_modif_bychgset')
    user_md = group_stats(user_md, chgset_md, 'uid', 'n_elem',
                              'n', '_elem_bychgset')

    # Update features
    user_md = group_stats(user_md, osm_elements, 'uid', 'nextmodif_in',
                              't', '_update_inhour')
    osmelem_corr = osm_elements.query("willbe_corr")
    user_md = group_stats(user_md, osmelem_corr, 'uid', 'nextcorr_in',
                              't', '_corr_h')
    user_md = group_count(user_md, osmelem_corr, 'uid', 'willbe_corr',
                              '_corr')
    osmelem_autocorr = osm_elements.query("willbe_autocorr")
    user_md = group_stats(user_md, osmelem_autocorr, 'uid',
                              'nextauto_in', 't', '_autocorr_h')
    user_md = group_count(user_md, osmelem_autocorr, 'uid',
                              'willbe_autocorr', '_autocorr')

    # Modification-related features
    user_md = group_count(user_md, osm_elements, 'uid', 'id', '_modif')
    #
    osmmodif_cr = osm_elements.query("init")        
    user_md = group_count(user_md, osmmodif_cr, 'uid', 'id',
                              '_modif_cr')
    osmmodif_cr_utd = osmmodif_cr.query("up_to_date")
    user_md = group_count(user_md, osmmodif_cr_utd, 'uid', 'id',
                              '_modif_crutd')
    osmmodif_cr_mod = osmmodif_cr.query("not up_to_date and available")
    user_md = group_count(user_md, osmmodif_cr_mod, 'uid', 'id',
                              '_modif_crmod')
    osmmodif_cr_del = osmmodif_cr.query("not up_to_date and not available")
    user_md = group_count(user_md, osmmodif_cr_del, 'uid', 'id',
                              '_modif_crdel')
    #
    osmmodif_del = osm_elements.query("not init and not visible")
    user_md = group_count(user_md, osmmodif_del, 'uid', 'id',
                              '_modif_del')
    osmmodif_del_utd = osmmodif_del.query("not available")
    user_md = group_count(user_md, osmmodif_del_utd, 'uid', 'id',
                              '_modif_delutd')
    osmmodif_del_rebirth = osmmodif_del.query("available")
    user_md = group_count(user_md, osmmodif_del_rebirth, 'uid', 'id',
                              '_modif_delrebirth')
    user_md = group_stats(user_md, osmmodif_del, 'uid', 'version',
                              'v', '_modif_del')
    #
    osmmodif_imp = osm_elements.query("not init and visible")
    user_md = group_count(user_md, osmmodif_imp, 'uid', 'id',
                              '_modif_imp')
    osmmodif_imp_utd = osmmodif_imp.query("up_to_date")
    user_md = group_count(user_md, osmmodif_imp_utd, 'uid', 'id',
                              '_modif_imputd')
    osmmodif_imp_mod = osmmodif_imp.query("not up_to_date and available")
    user_md = group_count(user_md, osmmodif_imp_mod, 'uid', 'id',
                              '_modif_impmod')
    osmmodif_imp_del = osmmodif_imp.query("not up_to_date and not available")
    user_md = group_count(user_md, osmmodif_imp_del, 'uid', 'id',
                              '_modif_impdel')
    user_md = group_stats(user_md, osmmodif_imp, 'uid', 'version',
                              'v', '_modif_imp')

    # Number of modifications per unique element
    contrib_byelem = (osm_elements.groupby(['elem', 'id', 'uid'])['version']
                      .count()
                      .reset_index())
    user_md = group_stats(user_md, contrib_byelem, 'uid', 'version',
                              'n', '_modif_byelem')
    user_md = group_count(user_md, contrib_byelem.query("version==1"),
                              'uid', 'id', '_with_1_contrib')

    # User-related features
    user_md = group_nunique(user_md, osm_elements, 'uid', 'id', '')
    osmelem_cr = osm_elements.query("init and available")
    user_md = group_nunique(user_md, osmelem_cr, 'uid', 'id', '_cr')
    user_md = group_stats(user_md, osmelem_cr, 'uid', 'vmax',
                              'v', '_cr')
    osmelem_cr_wrong = osm_elements.query("init and not available")
    user_md = group_nunique(user_md, osmelem_cr_wrong, 'uid', 'id',
                                '_cr_wrong')
    user_md = group_stats(user_md, osmelem_cr_wrong, 'uid', 'vmax',
                              'v', '_cr_wrong')
    osmelem_imp = osm_elements.query("not init and visible and available")
    user_md = group_nunique(user_md, osmelem_imp, 'uid', 'id', '_imp')
    user_md = group_stats(user_md, osmelem_imp, 'uid', 'vmax',
                              'v', '_imp')
    osmelem_imp_wrong = osm_elements.query("not init and visible and not available")
    user_md = group_nunique(user_md, osmelem_imp_wrong, 'uid', 'id', '_imp_wrong')
    user_md = group_stats(user_md, osmelem_imp_wrong, 'uid', 'vmax',
                              'v', '_imp_wrong')
    osmelem_del = osm_elements.query("not init and not visible and not available")
    user_md = group_nunique(user_md, osmelem_del, 'uid', 'id', '_del')
    user_md = group_stats(user_md, osmelem_del, 'uid', 'vmax',
                              'v', '_del')
    osmelem_del_wrong = osm_elements.query("not init and not visible and available")
    user_md = group_nunique(user_md, osmelem_del_wrong, 'uid', 'id', '_del_wrong')
    user_md = group_stats(user_md, osmelem_del_wrong, 'uid', 'vmax',
                              'v', '_del_wrong')

    return user_md

def extract_features(data, pattern):
    """Extract features from data that respect the given string pattern

    Parameters
    ----------
    data: pd.DataFrame
    starting dataframe
    pattern: str
    character string that indicates which column has to be kept
    """
    return data[[col for col in data.columns
                 if re.search(pattern, col) is not None]].copy()

def drop_features(data, pattern):
    """Drop features from data that respect the given string pattern

    Parameters
    ----------
    data: pd.DataFrame
    starting dataframe
    pattern: str
    character string that indicates which column has to be dropped
    """
    return data[[col for col in data.columns
                 if re.search(pattern, col) is None]].copy()

def compute_pca_variance(X):
    """Compute the covariance matrix of X and the associated eigen values to
    evaluate the explained variance of the data

    Parameters
    ----------
    X: numpy 2D array
    data matrix, contain the values of the dataframe used as a basis for the
    PCA     """
    cov_mat = np.cov(X.T)
    eig_vals, eig_vecs = np.linalg.eig(cov_mat)
    eig_vals = sorted(eig_vals, reverse=True)
    tot = sum(eig_vals)
    varexp = [(i/tot)*100 for i in eig_vals]
    cumvarexp = np.cumsum(varexp)
    varmat = pd.DataFrame({'eig': eig_vals,
                           'varexp': varexp,
                           'cumvar': cumvarexp})[['eig','varexp','cumvar']]
    return varmat

def elbow_derivation(elbow, nbmin_clusters):
    """Compute a proxy of the elbow function derivative to automatically
    extract the optimal number of cluster; this number must be higher that
    nbmin_clusters
    Parameters
    ----------
    elbow: list
    contains value of the elbow function for each number of clusters
    nbmin_clusters: integer
    lower bound of the number of clusters
    """
    elbow_deriv = [0]
    for i in range(1, len(elbow)-1):
        if i < nbmin_clusters:
            elbow_deriv.append(0)
        else:
            elbow_deriv.append(elbow[i+1]+elbow[i-1]-2*elbow[i])
    return elbow_deriv
