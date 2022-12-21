import functions_framework
import io
import os
import warnings
import tempfile
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from google.cloud import storage
from PIL import Image
from datetime import date

bucket_name = os.environ.get('BUCKET')
stability_key = os.environ.get('STABILITY_API_KEY')

storage_client = storage.Client()
stability_api = client.StabilityInference(key=stability_key, verbose=True,)
base_prompt = ''
seed = 513912915

"""HTTP Cloud Function.
   Args:
       request (flask.Request): The http request object.
   Returns:
       A json response with the url to a generated and saved image.
"""
@functions_framework.http
def generate_image(request):
   prompt = request.args.get('prompt')
   image_info = {}

   # Prevent running if there is no provided prompt
   if not prompt:
      raise ValueError("Missing a 'prompt' query param")

   # fallback file name
   today = date.today().strftime('%Y-%m-%d')
   full_prompt = prompt + base_prompt

   print('bucket', bucket_name)
   print('api key', stability_key)
   print('today', today)
   print('full prompt', full_prompt)

   generated_image = sd_generate_image(full_prompt)
   image_info['url'] = save_image_to_storage(generated_image, today)

   return image_info

"""Stable Diffusion Generate Function
   Args:
       prompt (String): The text used to generate the image.
   Returns:
       A PIL Image generated by Stable Diffusion.
"""
def sd_generate_image(prompt):
  # the object returned is a python generator
  answers = stability_api.generate(
      prompt=prompt,
      steps=29,
      width=512,
      height=512,
      cfg_scale=15.0,
      samples=1,
      safety=True,
      seed=seed
  )

  # iterating over the generator produces the api response
  for resp in answers:
      for artifact in resp.artifacts:
          if artifact.finish_reason == generation.FILTER:
              raise Exception("Your request activated the API's safety filters and could not be processed. Please modify the prompt and try again.")
          if artifact.type == generation.ARTIFACT_IMAGE:
              img = Image.open(io.BytesIO(artifact.binary))

  return img

"""Save image to Cloud Storage
   Args:
       generated_image (PIL Image): the image to store.
       destination_file_name (String): the name to save the file as.
   Returns:
       A public URL of the stored image.
"""
def save_image_to_storage(generated_image, destination_file_name):
  # Create temp file with name
  _, temp_local_filename = tempfile.mkstemp(suffix='.jpg')

  print(temp_local_filename)

  # Save to temp file
  generated_image.save(temp_local_filename, generated_image.format, quality=100)

  # Upload result to a storage bucket
  bucket = storage_client.bucket(bucket_name)
  new_blob = bucket.blob(destination_file_name)
  new_blob.upload_from_filename(temp_local_filename)
  os.remove(temp_local_filename)
  return new_blob.public_url