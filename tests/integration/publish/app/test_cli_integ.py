import os
import time
import json
from subprocess import Popen, PIPE
from unittest import TestCase
import boto3

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


class TestPublishApp(TestCase):

    def setUp(self):
        self.region_name = "us-east-1"
        self.sar_client = boto3.client('serverlessrepo', region_name=self.region_name)
        self.test_data_path = Path(__file__).resolve().parents[2].joinpath("testdata", "publish")

        app_metadata_text = self.test_data_path.joinpath("metadata_create_app.json").read_text()
        app_metadata = json.loads(app_metadata_text)
        app_metadata['TemplateBody'] = self.test_data_path.joinpath("template_create_app.yaml").read_text()
        response = self.sar_client.create_application(**app_metadata)
        # Avoid race conditions
        time.sleep(1)
        self.application_id = response['ApplicationId']

    def base_command(self):
        command = "sam"
        if os.getenv("SAM_CLI_DEV"):
            command = "samdev"

        return command

    def get_command_list(self, template_path=None, region=None, profile=None):
        command_list = [self.base_command(), "publish", "app"]

        if template_path:
            command_list = command_list + ["-t", template_path]

        if region:
            command_list = command_list + ["--region", region]

        if profile:
            command_list = command_list + ["--profile", profile]

        return command_list

    def test_create_application(self):
        # Delete the app first before creating
        self.sar_client.delete_application(ApplicationId=self.application_id)
        # Avoid race conditions
        time.sleep(1)

        template_path = self.test_data_path.joinpath("template_create_app.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        process = Popen(command_list, stdout=PIPE)
        process.wait()
        process_stdout = b"".join(process.stdout.readlines()).strip()

        app_metadata = self.test_data_path.joinpath("metadata_create_app.json").read_text()
        expected_msg = "Created new application with the following metadata:\n{}".format(app_metadata)
        self.assertIn(expected_msg, process_stdout.decode('utf-8'))

    def test_update_application(self):
        template_path = self.test_data_path.joinpath("template_update_app.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        process = Popen(command_list, stdout=PIPE)
        process.wait()
        process_stdout = b"".join(process.stdout.readlines()).strip()

        app_metadata = self.test_data_path.joinpath("metadata_update_app.json").read_text()
        expected_msg = 'The following metadata of application "{}" has been updated:\n{}'.format(
            self.application_id, app_metadata)
        self.assertIn(expected_msg, process_stdout.decode('utf-8'))

    def test_create_application_version(self):
        template_path = self.test_data_path.joinpath("template_create_app_version.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        process = Popen(command_list, stdout=PIPE)
        process.wait()
        process_stdout = b"".join(process.stdout.readlines()).strip()

        app_metadata = self.test_data_path.joinpath("metadata_create_app_version.json").read_text()
        expected_msg = 'The following metadata of application "{}" has been updated:\n{}'.format(
            self.application_id, app_metadata)
        self.assertIn(expected_msg, process_stdout.decode('utf-8'))

    def test_publish_without_s3_permission(self):
        template_path = self.test_data_path.joinpath("template_no_s3_permission.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        process = Popen(command_list, stderr=PIPE)
        process.wait()
        process_stderr = b"".join(process.stderr.readlines()).strip()

        expected_msg = "AWS Serverless Application Repository doesn't have read permissions"
        self.assertIn(expected_msg, process_stderr.decode('utf-8'))

    def tearDown(self):
        self.sar_client.delete_application(ApplicationId=self.application_id)
        # Avoid race conditions
        time.sleep(1)
