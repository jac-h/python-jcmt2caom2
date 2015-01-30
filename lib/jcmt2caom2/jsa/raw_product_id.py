#################################
# Import required Python modules
#################################
import logging

from tools4caom2.error import CAOMError

from jcmt2caom2.__version__ import version
from jcmt2caom2.jsa.product_id import product_id

logger = logging.getLogger(__name__)


def raw_product_id(backend, context, jcmt_db, obsid, conn):
    """
    Generates raw (observationID, productID) values for an observation.

    Arguments:
    backend: one of ACSIS, DAS, AOS-C, SCUBA-2
    context: one of "raw", "prod"
    jcmt_db: prefix fot the database and schem where ACSIS, FILES are located
    obsid: observation identifier, primary key in COMMON table
    conn: connection to database

    Returns:
    if usage == "raw" return a dictionary of productID keyed on
                      subsysnr (filter for SCUBA-2)
    elif usage == "prod" return a dictionary of productID keyed on
                         file_id (minus .sdf extension)
    """
    if backend == 'SCUBA-2':
        subsysnr_dict = {'450': 'raw-450um',
                         '850': 'raw-850um'}
        if context == 'prod':
            sqlcmd = '\n'.join([
                     'SELECT substring(f.file_id, 1, len(f.file_id)-4),',
                     '       s.filter',
                     'FROM ' + jcmt_db + 'FILES f',
                     '    INNER JOIN ' + jcmt_db + 'SCUBA2 s',
                     '        ON f.obsid_subsysnr=s.obsid_subsysnr',
                     'WHERE f.obsid = "%s"' % (obsid,)])
            result = conn.read(sqlcmd)

            fileid_dict = {}
            if result:
                for file_id, filter in result:
                    fileid_dict[file_id] = (obsid,
                                            product_id(backend,
                                                       product='raw',
                                                       filter=str(filter)))
            else:
                raise CAOMError('no rows returned from FILES for obsid = ' +
                                obsid)

    else:
        subsysnr_dict = {}
        if backend == 'ACSIS':
            sqlcmd = '\n'.join([
                     'SELECT a.subsysnr,',
                     '       min(a.restfreq),',
                     '       min(a.bwmode),',
                     '       min(aa.subsysnr),',
                     '       count(aa.subsysnr)',
                     'FROM ' + jcmt_db + 'ACSIS a',
                     '    INNER JOIN ' + jcmt_db + 'ACSIS aa',
                     '        ON a.obsid=aa.obsid',
                     '        AND a.restfreq=aa.restfreq',
                     '        AND a.iffreq=aa.iffreq',
                     '        AND a.ifchansp=aa.ifchansp',
                     'WHERE a.obsid = "%s"' % (obsid,),
                     'GROUP BY a.subsysnr'])
        elif backend in ['DAS', 'AOS-C']:
            sqlcmd = '\n'.join([
                     'SELECT a.subsysnr,',
                     '       a.restfreq,',
                     '       a.bwmode,',
                     '       a.specid,',
                     '       count(aa.subsysnr)',
                     'FROM ' + jcmt_db + 'ACSIS a',
                     '    INNER JOIN ' + jcmt_db + 'ACSIS aa',
                     '        ON a.obsid=aa.obsid',
                     '        AND a.specid=aa.specid',
                     'WHERE a.obsid = "%s"' % (obsid,),
                     'GROUP BY a.subsysnr, a.restfreq, a.bwmode, a.specid'])
        else:
            raise CAOMError('backend = ' + backend + ' is not supported')

        result = conn.read(sqlcmd)
        if result:
            for subsysnr, restfreq, bwmode, specid, hybrid in result:
                restfreqhz = 1.0e9 * float(restfreq)
                prefix = 'raw'
                if int(hybrid) > 1:
                    prefix = 'raw-hybrid'
                subsysnr_dict[str(subsysnr)] = product_id(backend,
                                                          product=prefix,
                                                          restfreq=restfreqhz,
                                                          bwmode=bwmode,
                                                          subsysnr=str(specid))
        else:
            raise CAOMError('no rows returned from ACSIS for obsid = ' + obsid)

        if context == 'prod':
            sqlcmd = '\n'.join([
                     'SELECT substring(f.file_id, 1, len(f.file_id)-4),',
                     '       a.subsysnr',
                     'FROM ' + jcmt_db + 'FILES f',
                     '    INNER JOIN ' + jcmt_db + 'ACSIS a',
                     '        ON f.obsid_subsysnr=a.obsid_subsysnr',
                     'WHERE f.obsid = "%s"' % (obsid,)])
            result = conn.read(sqlcmd)

            fileid_dict = {}
            if result:
                for file_id, subsysnr in result:
                    fileid_dict[file_id] = (obsid,
                                            subsysnr_dict[str(subsysnr)])
                    logger.debug('file_id metadata: %s, %s, %s',
                                 file_id, obsid, subsysnr_dict[str(subsysnr)])
            else:
                raise CAOMError('no rows returned from FILES for obsid = ' +
                                obsid)

    if context == 'raw':
        return subsysnr_dict
    elif context == 'prod':
        return fileid_dict
