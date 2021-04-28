import json
from ftplib import FTP
import os
from os import path
from pymongoClient import client


class ftpDownloader:
    """
    Class that allows the downloading of files through the FTP protocol
    """
    def __init__(self):
        self.URL = None
        self.file_location = None
        self.file = None
        self.output_dir = None

    def update_url(self, url):
        """
        If the root url changes whild looping through the files update the url information
        :param url: The new URL
        :return:
        """
        seperation = self.seperateURL(url)

        if seperation[0] != self.URL:
            print("Root URL changed")
            self.URL = seperation[0]
            self.connect()

        file = seperation[1].rsplit('/', 1)
        self.file_location = file[0]
        self.file = file[1]

    def update_output_dir(self, output_dir):
        """
        Updates the output directory
        :param output_dir: new output dir
        :return:
        """
        self.output_dir = output_dir

    def seperateURL(self, URL):
        """
        Splits the URL into a root server and file path
        :param URL:
        :return:
        """
        sections = URL.split("/", 1)
        return sections

    def connect(self):
        """
        Connects to the ftp server
        :return:
        """
        print("Connecting to ftp server")
        self.connection = FTP(self.URL, timeout=60)
        self.connection.login('anonymous', '')

    def download(self):
        """
        Downloads a file
        :return:
        """
        # Restore directory to root
        self.connection.cwd("~")
        self.connection.cwd(self.file_location)
        self.connection.retrbinary("RETR " + self.file, open(os.path.join(self.output_dir, self.file), 'wb').write)

    def close(self):
        self.connection.close()


class retrieveFromTable:
    """
    Parses the data provided in a json table ino samples that can be downloaded
    """
    def __init__(self, jsonTable, outputDir):
        self.data = self.parseTable(jsonTable)
        self.outputDir = "./" + outputDir
        self.dbClient = client.dbClient()
        self.downloadProcess()
        self.dbClient.close()

    def checkExists(self, path):
        """
        Check the output filepath exists
        :param path: Path for the ouput
        :return:
        """
        if not os.path.exists(path):
            os.makedirs(path)
            return True
        return False

    def parseTable(self, jsonTable):
        """
        Parse the json table into a useable format
        :param jsonTable:
        :return:
        """
        try:
            exists = path.exists(jsonTable)
            with open(jsonTable, "r") as f:
                return json.loads(f.read())
        except:
            return json.loads(jsonTable)

    def downloadProcess(self):
        """
        Loop thorugh the table and download each file specified
        :return:
        """
        print("Starting Download Process for " + str(len(self.data)), "Samples")
        ftp = ftpDownloader()
        for sample in self.data:
            path = os.path.join(self.outputDir, sample['run_accession'])
            if self.checkExists(path):
                ftp.update_url(sample['fastq_ftp'])
                ftp.update_output_dir(path)
                ftp.download()
            self.insertDB(sample, path)
            print("Sample", str(self.data.index(sample)), "Downloaded")
        ftp.close()

    def insertDB(self, sampleData, path):
        """
        Inserts the information about each sample into the database
        :param sampleData: The data about the sample
        :param path: The path the sample data was stored at
        :return:
        """
        if sampleData['sample_alias'] != sampleData['study_accession']:
            try:
                sampleData['sample_alias'] = sampleData['sample_alias'].split('.')[1]


            except:
                print("Sample Alias of atypical type.")
                print("Sample has been discounted from the system but can be added via manual review"+
                      " or by changing the alias in the provided json file")
        sampleData['file_location'] = path

        if self.dbClient.check_doc_exists({"run_accession": sampleData['run_accession']}, "samples"):
            print("study_accession " + sampleData['run_accession'] + " already exists, ignored the additional instances")
            print("Ensure that there are no repeating instances of the same file")
        else:
            self.dbClient.insert_one(sampleData, "samples")


if __name__ == '__main__':
    ena_json_table = os.getenv('JSON_FILE')
    output_dir = os.getenv('OUTPUT_DIR')
    table = retrieveFromTable(ena_json_table, output_dir)

