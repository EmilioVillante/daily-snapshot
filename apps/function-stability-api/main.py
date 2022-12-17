import functions_framework
import io
import os
import warnings
import tempfile
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from google.cloud import storage
from PIL import Image

bucket_name = os.environ.get('BUCKET')
stability_key = os.environ.get('STABILITY_API')

print(bucket_name, stability_key)

storage_client = storage.Client()
stability_api = client.StabilityInference(key=stability_key, verbose=True,)
base_prompt = ' + , realistic, highly detailed, digital painting, concept art, smooth, sharp focus, illustration, cinematic lighting, ArtStation, art by greg rutkowski.'

@functions_framework.http
def generate_image(request):
   """HTTP Cloud Function.
   Args:
       request (flask.Request): The request object.
   Returns:
       A json response with the url to a generated and saved image.
   """
   print(request)

   request_json = request.get_json(silent=True)

   prompt = ""
   image_info = {}

   if request_json and 'prompt' in request_json:
      prompt = request_json['prompt']
   else:
      return ''

   generated_image = sd_generate_image(prompt=prompt)

   image_info['url'] = save_image_to_storage(generated_image)

   return image_info

def sd_generate_image(prompt):
  """Stable Diffusion Generate Function
   Args:
       prompt (String): The text used to generate the image.
   Returns:
       A PIL Image generated by Stable Diffusion.
  """
  # the object returned is a python generator
  full_prompt = prompt+base_prompt

  print(full_prompt)

  answers = stability_api.generate(
      prompt=full_prompt,
      steps=15,
      width=512,
      height=512,
      cfg_scale=8.0,
      samples=1,
      safety=True,
      seed=123
  )

  print(answers)

  # iterating over the generator produces the api response
  for resp in answers:
      for artifact in resp.artifacts:
          if artifact.finish_reason == generation.FILTER:
              raise Exception("Your request activated the API's safety filters and could not be processed. Please modify the prompt and try again.")
          if artifact.type == generation.ARTIFACT_IMAGE:
              img = Image.open(io.BytesIO(artifact.binary))

  print(img)

  return img

def save_image_to_storage(generated_image):
  """Cloud Storage
   Args:
       generated_image (PIL Image): the image to store.
   Returns:
       A public URL of the stored image.
  """
  # Create temp file with name
  _, temp_local_filename = tempfile.mkstemp(suffix='.jpg')

  print(temp_local_filename)

  # Save to temp file
  generated_image.save(temp_local_filename, generated_image.format, quality=100)

  # Upload result to a storage bucket
  bucket = storage_client.bucket(bucket_name)
  new_blob = bucket.blob(temp_local_filename)
  new_blob.upload_from_filename(temp_local_filename)
  os.remove(temp_local_filename)
  return new_blob.public_url