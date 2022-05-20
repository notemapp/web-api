import boto3
import dataclasses
import json
import os
import uuid
import botocore.exceptions

TABLE_NAME = os.environ['TABLE_NAME']
DYNAMODB = boto3.resource('dynamodb')
TABLE = DYNAMODB.Table(TABLE_NAME)


@dataclasses.dataclass
class Response:

    status_code: int
    body: dict


def get_random_note_id():

    return str(uuid.uuid4())


def get_note_by_id(id_):

    response = TABLE.get_item(Key={'id': id_})
    return response['Item'] if 'Item' in response else None


def create_note():

    id_ = get_random_note_id()
    TABLE.put_item(Item={'id': id_, 'geostrokes': []})

    return Response(status_code=200, body={'id': id_})


def get_note(note_id):

    note = get_note_by_id(note_id)
    if note:
        status_code, body = 200, note
    else:
        status_code, body = 404, {}

    return Response(status_code=status_code, body=body)


def create_stroke(note_id, request_body):

    if not request_body:
        return Response(status_code=400, body={})

    geostroke = request_body.get('geostroke')

    if geostroke:
        try:
            TABLE.update_item(
                Key={'id': note_id},
                UpdateExpression='SET #geostrokes = list_append(#geostrokes, :new_stroke)',
                ExpressionAttributeValues={':new_stroke': [geostroke]},
                ExpressionAttributeNames={'#geostrokes': 'geostrokes'}
            )
        except botocore.exceptions.ClientError:
            return Response(status_code=400, body={})

    return Response(status_code=200, body={'id': note_id})


def delete_stroke(note_id):

    note = get_note_by_id(note_id)
    if note:
        n_geostrokes = len(note['geostrokes'])
        if n_geostrokes > 0:
            TABLE.update_item(
                Key={'id': note_id},
                UpdateExpression='REMOVE #geostrokes[%d]' % (n_geostrokes - 1),
                ExpressionAttributeNames={'#geostrokes': 'geostrokes'}
            )
        status_code, body = 200, {'id': note_id}
    else:
        status_code, body = 404, {}

    return Response(status_code=status_code, body=body)


def handle(event):

    path, method = event['path'], event['httpMethod']
    body = json.loads(event['body']) if event.get('body') is not None else {}

    if path in ('/v1/note/', '/v1/note') and method == 'POST':
        return create_note()
    elif path.startswith('/v1/note/') and method == 'GET':
        return get_note(path.split('/')[-1])
    elif path.startswith('/v1/note/') and method == 'POST':
        return create_stroke(path.split('/')[-2], body)
    elif path.startswith('/v1/note/') and method == 'DELETE':
        return delete_stroke(path.split('/')[-2])


def lambda_handler(event, _):

    response = handle(event)

    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.body),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Methods': '*'
        }
    }
