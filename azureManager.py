import os
import shutil
import datetime

from azure.storage.blob import BlobServiceClient, ContainerClient


class AzureManager():
    def __init__(self):
        # gets the enviromnent variable that contains the azure connection string
        try:
            self.connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        except:
            print('connect str env variable not set')

        self.species = self.list_all_plant_containers()

    def list_all_plant_containers(self):
        connect_str = self.connect_str
        # Create the BlobServiceClient object which will be used to create a container client
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        all_containers = blob_service_client.list_containers(include_metadata=True)
        species_list = []
        for container in all_containers:
            name = container['name']
            # disregard the folder if it is the models folder
            if name != 'models':
                species_list.append(name)
        return species_list

    def create_container(self, container_name):
        # Create the BlobServiceClient object which will be used to create a container client
        blob_service_client = BlobServiceClient.from_connection_string(self.connect_str)

        # check if container doesn't exist yet
        if container_name not in self.species:
            # Create a unique name for the container
            try:
                # Create the container
                container_client = blob_service_client.create_container(container_name)
            except:
                return False

    # uploads all the models that are saved locally
    def upload_pictures(self):
        try:
            connect_str = self.connect_str
            # Create the BlobServiceClient object which will be used to create a container client
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)

            image_path = 'static/images/'

            for specie in os.listdir(image_path):
                for image in os.listdir(image_path):
                    blob_client = blob_service_client.get_blob_client(container=str(specie), blob=image)

                    print("\nUploading to Azure Storage as blob:\n\t" + image)

                    image = image_path + image
                    # Upload the created file

                    with open(image, "rb") as data:
                        try:
                            blob_client.upload_blob(data)
                        except:
                            print("file already exists")
        except IOError as e:
            print(e)

    def upload_single_picture(self, filename, species):
        try:
            connect_str = self.connect_str
            # Create the BlobServiceClient object which will be used to create a container client
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)

            image_path = 'static/images/'
            blob_client = blob_service_client.get_blob_client(container=species, blob=filename)

            print("\nUploading to Azure Storage as blob:\n\t" + filename)

            image = image_path + '/' + species + '/' + filename
            # Upload the created file

            with open(image, "rb") as data:
                try:
                    blob_client.upload_blob(data)
                except:
                    print("file already exists")
        except IOError as e:
            print(e)

    def download_all_models(self):
        try:
            connect_str = self.connect_str
            # Create the BlobServiceClient object which will be used to create a container client
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)

            container_client = ContainerClient.from_connection_string(conn_str=connect_str, container_name='models')
            file_path = 'static/models/'
            if not os.path.exists(file_path):
                print("making model folder")
                os.makedirs(file_path)

            blob_list = container_client.list_blobs()
            for blob in blob_list:
                print(blob.name + '\n')

                bc = blob_service_client.get_blob_client(container='models', blob=blob)
                filename = blob.name
                try:
                    with open(file_path + filename, 'wb') as file:
                        data = bc.download_blob()
                        file.write(data.readall())
                except IOError as e:
                    print(e)
        except Exception as ex:
            print('Exception:')
            print(ex)

    # get latest model to use for classifying
    def get_latest_model(self):
        folder = 'static/models'
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

        try:
            connect_str = self.connect_str
            # Create the BlobServiceClient object which will be used to create a container client
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)

            container_client = ContainerClient.from_connection_string(conn_str=connect_str, container_name='models')
            file_path = 'static/models/'
            if not os.path.exists(file_path):
                print("making model folder")
                os.makedirs(file_path)

            blob_list = container_client.list_blobs()

            list_modelblobs = []
            for blob in blob_list:
                list_modelblobs.append([blob.last_modified, blob])

            most_recent_timestamp = list_modelblobs[0][0]
            most_recent_blob = list_modelblobs[0][1]
            for models in list_modelblobs:
                blob_time = models[0]
                if blob_time > most_recent_timestamp:
                    most_recent_timestamp = blob_time
                    most_recent_blob = models[1]

            bc = blob_service_client.get_blob_client(container='models', blob=most_recent_blob)
            filename = most_recent_blob.name
            try:
                with open(file_path + filename, 'wb') as file:
                    data = bc.download_blob()
                    file.write(data.readall())
            except IOError as e:
                print(e)
        except ValueError as e:
            print('something went wrong, there might not have been a model saved in the cloud'+e)