"""MongoDB aggregation: cohorts and latest per-modality precomputed comparisons."""
import csv
import io
from flask import Blueprint, Response, request
from .auth import auth_required
from .common import choice, db, query_args, response, string
from .samples import FILTERS, filters

bp = Blueprint('analytics', __name__)

def age_group():
    return {'$switch': {'branches': [
        {'case': {'$eq': ['$age_at_scan_weeks', None]}, 'then': 'unknown'},
        {'case': {'$lt': ['$age_at_scan_weeks', 32]}, 'then': '<32 weeks'},
        {'case': {'$lt': ['$age_at_scan_weeks', 37]}, 'then': '32-<37 weeks'},
        {'case': {'$lt': ['$age_at_scan_weeks', 42]}, 'then': '37-<42 weeks'}], 'default': '>=42 weeks'}}

def cohort_rows(query):
    return list(db().samples.aggregate([{'$match': query}, {'$group': {
        '_id': {'age_group': age_group(), 'source': '$source'}, 'sample_count': {'$sum': 1},
        'dmri_count': {'$sum': {'$cond': ['$has_dmri', 1, 0]}},
        'fmri_count': {'$sum': {'$cond': ['$has_fmri', 1, 0]}},
        'mean_scan_age_weeks': {'$avg': '$age_at_scan_weeks'}}}, {'$sort': {'_id.source': 1, '_id.age_group': 1}}]))

def result_filter(names):
    return {"analyses." + field: string(request.args[param], param, 120)
        for param, field in names.items() if param in request.args}

def maturity_rows(query, selected=None, group_by="overall"):
    # Choose the latest result for each sample and modality, so repeated analyses do not overweight a sample.
    groups = {'modality': '$_id.modality', 'source': '$source'}
    if group_by == 'age_group':
        groups['age_group'] = '$age_group'
    return list(db().samples.aggregate([{'$match': query}, {'$set': {'age_group': age_group()}}, {'$unwind': '$analyses'},
        {'$match': selected or {}}, {'$sort': {'analyses.created_at': -1, 'analyses._id': -1}},
        {'$group': {'_id': {'sample': '$_id', 'modality': '$analyses.modality'},
            'result': {'$first': '$analyses'}, 'age_group': {'$first': '$age_group'}, 'source': {'$first': '$source'}}},
        {'$group': {'_id': groups,
            'sample_count': {'$sum': 1}, 'difference_count': {'$sum': {'$cond': [{'$ne': ['$result.age_difference_weeks', None]}, 1, 0]}}, 'mean_estimated_age_weeks': {'$avg': '$result.estimated_age_weeks'},
            'mean_age_difference_weeks': {'$avg': '$result.age_difference_weeks'}}},
        {'$sort': {'_id.source': 1, '_id.modality': 1}}]))

def comparison_rows(query, selected=None):
    return list(db().samples.aggregate([{'$match': query}, {'$unwind': '$analyses'},
        {'$match': {'analyses.modality': {'$in': ['dmri', 'fmri']}}},
        {'$match': selected or {}},
        {'$sort': {'analyses.created_at': -1, 'analyses._id': -1}},
        {'$group': {'_id': {'sample': '$_id', 'modality': '$analyses.modality'},
            'estimate': {'$first': '$analyses.estimated_age_weeks'}, 'source': {'$first': '$source'}}},
        {'$group': {'_id': '$_id.sample', 'source': {'$first': '$source'},
            'results': {'$push': {'k': '$_id.modality', 'v': '$estimate'}}}},
        {'$match': {'results': {'$size': 2}}}, {'$set': {'pair': {'$arrayToObject': '$results'}}},
        {'$group': {'_id': '$source', 'paired_sample_count': {'$sum': 1},
            'mean_dmri_minus_fmri_weeks': {'$avg': {'$subtract': ['$pair.dmri', '$pair.fmri']}}}},
        {'$sort': {'_id': 1}}]))

@bp.get('/statistics/overview')
@auth_required()
def overview():
    query_args(FILTERS)
    result = list(db().samples.aggregate([{'$match': filters()}, {'$facet': {
        'total': [{'$count': 'count'}],
        'by_status': [{'$group': {'_id': '$status', 'count': {'$sum': 1}}}, {'$sort': {'_id': 1}}],
        'by_source': [{'$group': {'_id': '$source', 'count': {'$sum': 1}}}, {'$sort': {'_id': 1}}],
        'modalities': [{'$group': {'_id': None, 'dmri': {'$sum': {'$cond': ['$has_dmri', 1, 0]}},
            'fmri': {'$sum': {'$cond': ['$has_fmri', 1, 0]}},
            'both': {'$sum': {'$cond': [{'$and': ['$has_dmri', '$has_fmri']}, 1, 0]}}}}]}}]))[0]
    result['total'] = result['total'][0]['count'] if result['total'] else 0
    return response({'data': result})

@bp.get('/statistics/cohorts')
@auth_required()
def cohorts():
    query_args(FILTERS)
    return response({'data': cohort_rows(filters()), 'unit': 'postmenstrual weeks at scan'})

@bp.get('/statistics/maturity')
@auth_required()
def maturity():
    query_args(FILTERS | {'method', 'model_version', 'group_by'})
    selected = result_filter({'method': 'method', 'model_version': 'model_version'})
    group_by = choice(request.args.get('group_by', 'overall'), 'group_by', ('overall', 'age_group'))
    return response({'data': maturity_rows(filters(), selected, group_by), 'selection': {k: v for k, v in request.args.items() if k in ('method', 'model_version', 'group_by')}, 'interpretation': 'Descriptive summary of supplied results; no diagnostic classification. Unfiltered models may be mixed.'})

@bp.get('/statistics/comparison')
@auth_required()
def comparison():
    keys = {'dmri_method', 'dmri_model_version', 'fmri_method', 'fmri_model_version'}
    query_args(FILTERS | keys)
    alternatives = []
    for mode in ('dmri', 'fmri'):
        selected = result_filter({mode + '_method': 'method', mode + '_model_version': 'model_version'})
        alternatives.append({'analyses.modality': mode, **selected})
    return response({'data': comparison_rows(filters(), {'$or': alternatives}), 'selection': {k: v for k, v in request.args.items() if k in keys}, 'comparison': 'Latest matching dMRI minus latest matching fMRI estimate for paired samples only; unfiltered models may be mixed.'})

@bp.get('/exports/cohorts')
@auth_required()
def export_cohorts():
    query_args(FILTERS | {'format'})
    fmt = choice(request.args.get('format', 'json'), 'format', ('json', 'csv'))
    rows = cohort_rows(filters())
    if fmt == 'json':
        return response({'data': rows})
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['age_group', 'source', 'sample_count', 'dmri_count', 'fmri_count', 'mean_scan_age_weeks'])
    for row in rows:
        writer.writerow([row['_id']['age_group'], row['_id']['source'], row['sample_count'], row['dmri_count'], row['fmri_count'], row['mean_scan_age_weeks']])
    return Response(buffer.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="cohorts.csv"'})
