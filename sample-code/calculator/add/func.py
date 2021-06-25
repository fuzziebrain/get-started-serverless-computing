import io
import json
import logging

from fdk import response

def handler(ctx, data: io.BytesIO = None):
    sum = 0
    try:
        body = json.loads(data.getvalue())
        first_addend = body.get("first_addend")
        second_addend = body.get("second_addend")
        sum = first_addend + second_addend
    except (Exception, ValueError) as ex:
        logging.getLogger().info('error parsing json payload: ' + str(ex))

    logging.getLogger().info("Performing calculation.")
    return response.Response(
        ctx, response_data=json.dumps({"sum": sum }),
        headers={"Content-Type": "application/json"}
    )
