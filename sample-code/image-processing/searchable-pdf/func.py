import io
import json
import logging
import oci.object_storage
import os

from fdk import response
from PIL import Image
import pytesseract
import cv2

OBJECT_CREATE_EVENT = 'com.oraclecloud.objectstorage.createobject'
OBJECT_UPDATE_EVENT = 'com.oraclecloud.objectstorage.updateobject'
OBJECT_DELETE_EVENT = 'com.oraclecloud.objectstorage.deleteobject'

TEMP_DIR = '/tmp'
OUTPUT_DIR = os.path.join(TEMP_DIR, 'output')

def get_object(client, bucketName, objectName):
    namespace = client.get_namespace().data

    logging.getLogger().debug('Retrieving object {} from {}.'.format(objectName, bucketName))
    object = client.get_object(namespace, bucketName, objectName)
    if object.status == 200:
        message = 'Object found'
        logging.getLogger().info(message)
        logging.getLogger().debug('header: ' + object.headers['content-type'])

        file = open(os.path.join(TEMP_DIR, objectName), 'wb+')
        for chunk in object.data.raw.stream(2048 ** 2, decode_content = False):
            file.write(chunk)
        file.close()
    else:
        raise Exception('Failed: The object ' + objectName + ' could not be retrieved.')

    return { "content-type": object.headers['content-type'] }

def put_object(client, bucketName, pdfFilename):
    namespace = client.get_namespace().data
    mimeType = 'application/pdf'
    content = open(os.path.join(OUTPUT_DIR, pdfFilename), 'rb')

    try:
        logging.getLogger().debug('Uploading object {} to {}.'.format(pdfFilename, bucketName))
        object = client.put_object(
            namespace_name = namespace
            , bucket_name = bucketName
            , object_name = pdfFilename
            , content_type = mimeType
            , put_object_body = content
        )
    except Exception as e:
        logging.getLogger().exception(e)
        raise
    finally:
        content.close()

def delete_object(client, bucketName, objectName):
    namespace = client.get_namespace().data
    logging.getLogger().debug('Deleting object {} to {}.'.format(objectName, bucketName))
    response = client.delete_object(namespace, bucketName, objectName)

def generate_searchable_pdf(objectName, pdfFilename):
    logging.getLogger().debug('Generating searchable PDF.')

    if os.path.exists(OUTPUT_DIR) == False:
        os.mkdir(OUTPUT_DIR)

    input = cv2.imread(os.path.join(TEMP_DIR, objectName))
    input = cv2.cvtColor(input, cv2.COLOR_BGR2GRAY)
    input = cv2.threshold(input, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    output = pytesseract.image_to_pdf_or_hocr(input, extension='pdf')
    with open(os.path.join(OUTPUT_DIR, pdfFilename), 'w+b') as output_file:
        output_file.write(output)

# FDK Handler (Entry point)
def handler(ctx, data: io.BytesIO = None):
    # Send debugging output to OCI Logging
    logging.getLogger().debug('Received incoming request')

    # Use OCI resource principal to authenticate to call OCI REST APIs
    signer = oci.auth.signers.get_resource_principals_signer()

    # Obtain a client to work with Object Storage.
    client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    result_body = None

    # Retrieve the Function's configuration values that are accessed through the 
    # container's environment variables.
    pdf_bucket_name = os.environ['output_bucket']

    logging.getLogger().debug('Target bucket: ' + pdf_bucket_name)

    try:
        # Parse the input payload that is, by default, in JSON format.
        body = json.loads(data.getvalue())

        # Since the function is triggered by an OCI Event, we can obtain some
        # metadata about the object that triggered the Function.
        resourceId = body['data']['resourceId']
        objectName = body['data']['resourceName']
        bucketName = body['data']['additionalDetails']['bucketName']
        pdfFilename = os.path.splitext(objectName)[0] + '.pdf'

        logging.getLogger().info('Object name: {}'.format(resourceId))
        logging.getLogger().info('Object name: {}'.format(objectName))
        logging.getLogger().info('Bucket name: {}'.format(bucketName))

        if body['eventType'] in (OBJECT_CREATE_EVENT, OBJECT_UPDATE_EVENT):
            # First, retrieve the object that triggered the event and download
            # it to the the temporary directory of the container. The method 
            # also returns the content type.
            response_message = get_object(client, bucketName, objectName)

            if (response_message["content-type"].startswith('image/')):
                # If the object is of the MIME type "image", then generate a
                # thumbnail.
                generate_searchable_pdf(objectName, pdfFilename)

                # When done, upload the generated thumbnail to the designated
                # Object Storage bucket.
                put_object(client, pdf_bucket_name, pdfFilename)

            # Clean up files
            os.remove(os.path.join(TEMP_DIR, objectName))
            os.remove(os.path.join(OUTPUT_DIR, pdfFilename))
        elif body['eventType'] == OBJECT_DELETE_EVENT:
            # Delete the corresponding thumbnail object.
            delete_object(client, pdf_bucket_name, pdfFilename)
        else:
            logging.getLogger().info('Nothing to do.')
    except Exception as e:
        logging.getLogger().exception(e)
        result_body = { "status": "failed", "error-message": e }

    result_body = { "status": "success" }

    return response.Response(ctx, response_data=result_body)
