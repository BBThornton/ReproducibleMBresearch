from pymongo import MongoClient, errors
import os
import logging
class dbClient:

    def __init__(self):
        """
        A client that contains a number of shared features for interacting with the datbase architecture of the system
        This class provides a number of commonly used feeatures that are needed to
        retrieve and store results from previous experiments
        """
        self.client = self.start_connection()
        self.database = self.client["metagenomic"]

    def start_connection(self):
        """
        Create a connection between the current container and the mongo DB datbase
        :return: The client connection
        """
        try:
            # try to instantiate a client instance
            client = MongoClient(
                host='database',
                port=27017,
                serverSelectionTimeoutMS=3000,  # 3 second timeout
            )
            return client
        except errors.ServerSelectionTimeoutError as err:
            # catch pymongo.errors.ServerSelectionTimeoutError
            print("pymongo ERROR:", err)

    def insert_one(self, data, collection):
        """
        Insert a single json data object into the database at the specified colletion
        :param data: The json data object
        :param collection: The name of the collection to enter the object into
        :return: NONE
        """
        coll = self.database[collection]
        coll.update(data, data, upsert=True);

    def insert_many(self, data, collection):
        """
        Insert multiple objects into the specified collection
        :param data: The json data object
        :param collection: The name of the collection to enter the object into
        :return: NONE
        """
        coll = self.database[collection]
        coll.update_many(data, data, upsert=True)

    def query(self, query, collection):
        """
        Get a selection of objects from a collection that satisfy a query
        :param query: A mondodb query (in the form of a dictionary)
        :param collection: The collection to query
        :return: The list of all objects that satisfy the query
        """
        coll = self.database[collection]
        docs = coll.find(query)
        return docs

    def check_doc_exists(self, query, collection):
        """
        Checks if an object of the given specification exists in the specified collection
        :param query: The item to check exists
        :param collection: The collection to check for the item
        :return: True: document exists / False: Doesnt exist
        """
        coll = self.database[collection]
        if coll.count_documents(query, limit=1) == 0:
            return False
        else:
            return True

    def new_experiment(self, json_object):
        """
        Enter a new experiment object into the database
        :param json_object: The experiment json object
        :return: NONE
        """
        coll = self.database["experiment"]
        coll.insert_one(json_object)

    def get_one(self, query, collection):
        """
        Get a single item from a collection that satisfies the query
        :param query: The conditions for the object to be returned
        :param collection: The collection to check
        :return: The first object that satisfies the condition
        """
        coll = self.database[collection]
        docs = coll.find_one(query)
        return docs

    def get_one_selective(self, query, return_fields, collection):
        """
        Get a single item from a collection that satisfies the query
        but only return the data specified in return fields
        :param query: The conditions for the object to be returned
        :param return_fields: The attributes of the object to return (dict)
        :param collection: The collection to check
        :return: The document with only the specified headers
        """
        coll = self.database[collection]
        docs = coll.find_one(query, return_fields)
        return docs

    def post_order_traversal(self, node, visited):
        """
        A post order tree traversal method for searching the service tree
        Will return all the children between the current node and a leaf that havent been visited
        :param node: The current node being visited
        :param visited:
        :return: The children of the current node that haven't already been visited
        """
        coll = self.database["experiment"]
        visited.append(node["_id"])
        # All the chilren of the current node
        current_children = [i for i in coll.find({"parent": node["_id"]})]

        # Will get all the children of the current children that havent already been visited
        if len(current_children) > 0:
            for child in current_children:
                if child["_id"] not in visited:
                    return current_children + self.post_order_traversal(child, visited)
        else:
            return []

    def get_specified_parent_stage(self, target_stage, experiments, visited):
        """
        A tree search that searches through all the services until it finds the services with the same type as the
        target stage. This will search every node that is operated before the current stage by using post order tree
        traversal.
        Does not deal with an experiment not existing as it assumed that this will always be the case. This is because
        the initial experiment passed is always the first parent of the current experiment which is checked for existence
        in each docker image. This means that all the
        :param target_stage: The stage that the returned value must be a part of
        :param experiments: The experiments to search through
        :param visited: The experiments that have already been visited
        :return:
        """
        coll = self.database["experiment"]
        parent = coll.find_one({"_id": experiments[0]["_id"]})
        if parent["stage"] == target_stage:
            return parent
        else:

            visited.append(parent["_id"])
            children = coll.find({"parent": parent["_id"]})
            # Will get all the nodes that are connected to the children of the current node
            for child in children:
                if child["_id"] not in visited:
                    all_children = [child]
                    child_return = self.post_order_traversal(child, visited)
                    if child_return is not None:
                        # Adds all the childs children to the list
                        all_children.extend(child_return)
                    experiments.extend(all_children)

            current_exp_parent = coll.find_one({"_id": experiments[0]["parent"]})
            if current_exp_parent["_id"] not in visited:
                experiments.append(current_exp_parent)
            experiments.pop(0)
            if not experiments:
                return None

            return self.get_specified_parent_stage(target_stage, experiments, visited)

    def stage_parent_correct(self, current_stage, parent_experiment):
        """
        Check to make sure the parent experiment is of the correct type for the current stage experiment
        :param current_stage: The current stage of analysis
        :param parent_experiment: The parent experiment that has been passed via docker
        :return: The parent stage if it is valid or None otherwise
        """
        coll = self.database["experiment"]
        parent = coll.find_one({"_id": parent_experiment})
        if parent is not None:
            coll = self.database["services"]
            parent_stage = coll.find_one({"_id": current_stage})["parent"]
            if parent["stage"] == parent_stage:
                return parent
        return None


    def default_result_output_loc(self, stage, output_dir):
        """
        Get the default output locations as defined in the database services collection
        These are defined when the database is created via the service_defs.json file
        :param stage: The stage to get the defaults for
        :param output_dir: The root output directory for the service passed as a docker param
        :return: The list of output dirs for all the services
        """
        dirs = {"data": output_dir, "visuals": os.path.join(output_dir, "Visuals")}

        result = []
        services = self.database["services"]
        file_names = services.find_one({"_id": stage})["output"]

        for (k, v) in file_names.items():
            if v is not None:
                result.extend([os.path.join(dirs[k], item) for item in v])
                if not os.path.exists(dirs[k]):
                    os.makedirs(dirs[k])

        return result

    def close(self):
        """
        Close the db connection
        :return: NONE
        """
        self.client.close()
