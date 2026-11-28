"""Reviewed presentation settings; source height ranges remain separately recorded."""


def presentation(record):
    grass=record['look_id']=='EnvironmentDioramaGrass'
    return {'ReliefCm':1.0 if grass else record['height']['range_cm'], 'HeightMip':2 if grass else 0}
