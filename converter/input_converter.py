# -*- coding: utf-8 -*-
"""Converts Rich Capacitated Arc Routing Problems (RCARPS) raw input data into
python a class based format and stores the results as python objects. Used for
the heuristics of Willemse [1]. Return the python objects to be used by solution
algorithms and other applications.

Currently only supports the raw input file format of Belenguer et al [2].

References:

    [1] Willemse ,E.J. (2016). Heuristics for large-scale Capacitated Arc
        Routing Problems on mixed networks. PhD thesis, University of Pretoria,
        Pretoria. Available online from
        http://hdl.handle.net/2263/57510 (Last viewed on 2017-01-16).

    [2] Belenguer, J., Benavent, E., Lacomme, P., and Prins, C. (2006). Lower
        and upper bounds for the mixed capacitated arc routing problem.
        Computers & Operations Re- search, 33(12):3363--3383.

History:
    Created on 8 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import os
import pickle
from pprint import pprint
import converter.py_data_write as data_write
import converter.py_gen_nearest_neighbour_lists as gen_nn


class Converter(object):
    """Converts raw input for RCARPS into standardised objects for solution
    algorithms and writes the results to pickled files.
    """

    def __init__(self, instance_path=None, instance_folder=None,
                 output_folder=None, out_to_in=False, outfile_key=None,
                 overwrite=False):
        """Set the instance path to raw file, or to an instance folder
        with different instance files. Set the output path to write raw folders,
        and the file key name to use to write the output files, set
        whether intermediate folders should be created and whether existing
        files with identical names should be overwritten.

        Kwargs:
            instance_path (str): Path to the raw input file. If none is given,
                an instance folder is specified.
            instance_folder (str): Path to the folder containing multiple input
                files. If none is given an input file is specified.
            output_folder (str): Path to folder in which the converted data
                should be written. If none is given the current folder is used.
            out_to_in (bool): if the same input folder should be used to write
                the output.
            outfile_key (str): Key to use to write the different converted data
                files. If none is given the same name as the input file is used,
                preceding extensions.
            overwrite (bool): Overwrites existing data files that have the same
                name as the intended output files.

        TODO:
            Convert to _input_path instead of _instance_path
            Convert to _input_folder instead of _instance_folder.
        """

        self._instance_path = instance_path
        self._instance_folder = instance_folder
        self._output_folder = output_folder
        self._out_to_in = out_to_in
        self._outfile_key = outfile_key
        self._overwrite = overwrite

        self._output_extensions = ('_info_lists_pickled.dat',
                                   '_problem_info.dat',
                                   '_sp_data_full.dat',
                                   '_nn_list.dat')

        self._ignores = {'start': ['.'],
                         'extension': ['py']}

    def _check_basic_inputs(self):
        """Checks whether the basic class inputs are correct

        Raises:
            AttributeError: If errors in the class attributes were found.
                All errors are printed, not just the first one found.
        """

        errors = {}
        if self._instance_path is None and self._instance_folder is None:
            errors[0] = 'Either an instance path or instance folder ' \
                              'has to be specified.'

        if self._instance_path and self._instance_folder:
            errors[1] = 'Either an instance path or instance folder ' \
                              'has to be specified, not both.'

        if self._instance_path and not os.path.isfile(self._instance_path):
            errors[2] = 'Input file `{0}` not found.'.format(
                self._instance_path)

        if self._instance_folder is not None \
                and not os.path.isdir(self._instance_folder):
            errors[3] = 'Input folder `{0}` not found.'.format(
                self._instance_folder)

        if self._output_folder is not None \
                and not os.path.isdir(self._output_folder):
            errors[4] = 'Output folder `{0}` not found.'.format(
                self._output_folder)

        if self._instance_folder is not None and self._outfile_key is not None:
            errors[5] = 'Outfile key should be automatically generated when' \
                        ' input folder is specified.'

        if errors:
            pprint('{0} errors found in class attributes.'.format(
                len(errors)))
            pprint(errors)
            if 0 in errors or 5 in errors:
                raise AttributeError
            if 1 in errors:
                raise AttributeError
            if 2 in errors:
                raise FileNotFoundError
            if 3 in errors or 4 in errors:
                raise NotADirectoryError

    def _set_output_folder(self):
        """Set the output folder based on class initialisation attributes"""

        if self._output_folder is None:
            if not self._out_to_in:
                self._output_folder = '/'  # Set to the current directory.
            elif self._instance_folder:
                self._output_folder = self._instance_folder
            elif self._instance_path:
                folders = self._instance_path.split('/')
                if len(folders) > 0:
                    self._output_folder = '/'.join(folders[:-1]) + '/'
                else:
                    self._output_folder = '/'

    def _pad_folders(self):
        """Pad folders so that they end with '/'"""
        if self._instance_folder is not None \
                and self._instance_folder[-1] != '/':
            self._instance_folder += '/'

        if self._output_folder[-1] != '/':
            self._output_folder += '/'

    def _extract_key(self):
        """Extract file name key from input file path."""

        if self._outfile_key is None:
            file_name = self._instance_path.split('/')[-1]
            self._outfile_key = '.'.join(file_name.split('.')[:-1])

    def _check_output_files_exist(self):
        """Check if output files already exists if overwriting is deactive.

        Raises:
            FileExistsError: If output files already exist.
        """

        errors = []
        for ext in self._output_extensions:
            potential_out_file = self._output_folder + self._outfile_key + ext
            if os.path.isfile(potential_out_file):
                errors.append('`{0}` exists'.format(potential_out_file))

        if errors:
            if not self._overwrite:
                pprint('{0} errors found'.format(len(errors)))
                pprint(errors)
                raise FileExistsError
            else:
                pprint('{0} files will be overwritten'.format(len(errors)))
                pprint(errors)

        return errors

    def _write_data(self, data, extension):
        """Write info lists as python pickled objective to specified locations

        Args:
            data (class): python data object to be stored.
            extension (str): extension to be used in the file name.
        """
        output_file_path = self._output_folder + self._outfile_key + extension
        with open(output_file_path, 'wb') as output_file:
            pickle.dump(data, output_file)

    def convert_instance(self, check_inputs=True):
        """Converts the set input file, and stores the results

        Kwargs:
            check_inputs (bool): Whether the class settings should be checked
                for errors.
        """

        if check_inputs:
            self._check_basic_inputs()

        self._set_output_folder()
        self._pad_folders()
        self._extract_key()

        if check_inputs:
            self._check_output_files_exist()

        # Generate, return and write general arc info lists
        pprint('Converting {0}...'.format(self._instance_path))
        info_list = data_write.ArcConvertLists(self._instance_path)
        info_list_data = info_list.return_data()
        self._write_data(info_list_data, '_info_lists_pickled.dat')

        # Generate, return and write shortest path costs, and full instance info
        gen_sp_list = data_write.WriteSpIfInputData(info_list)
        (sp_info, instance_info_data) = gen_sp_list.return_sp_info(info_list)
        self._write_data(sp_info, '_sp_data_full.dat')
        self._write_data(instance_info_data, '_problem_info.dat')

        # Generate, return and write nearest neighbour lists based on SP.
        nn_lists = gen_nn.return_nn_lists(instance_info_data[-3])
        self._write_data(nn_lists, '_nn_list.dat')

    def _check_all_files_in_directory(self):
        """Check generation conditions for all non-python based files in a
        specified directory

        Raises:
            FileNotFoundError: If there are no files in the directory.
            Submodule: If output files already exist.
        """

        input_files = os.listdir(self._instance_folder)
        input_files_test = []
        for in_file in input_files:
            if os.path.isdir(in_file):
                continue
            if in_file[0] in self._ignores['start']:
                continue
            if in_file.split('.')[-1] in self._ignores['extension']:
                continue

            input_files_test.append(in_file)
            self._instance_path = self._instance_folder + in_file
            self._extract_key()
            self._check_output_files_exist()

        if not input_files_test:
            raise FileNotFoundError

        self._instance_path = None
        self._outfile_key = None

    def convert_multiple_instances(self, check_inputs=True):
        """Converts found input file in input file folder, and stores the
        results

        Kwargs:
            check_inputs (bool): Whether the class settings should be checked
                for errors.

        TODO:
            create a new class for converting multiple instances.
        """

        if check_inputs:
            self._check_basic_inputs()

        self._set_output_folder()
        self._pad_folders()

        if check_inputs:
            self._check_all_files_in_directory()

        input_files = os.listdir(self._instance_folder)
        for in_file in input_files:
            if in_file[0] in self._ignores['start']:
                continue
            if in_file.split('.')[-1] in self._ignores['extension']:
                continue

            instance_path = self._instance_folder + in_file

            # Create a new converter instance to write a single file.
            converter = Converter(instance_path=instance_path,
                                  instance_folder=None,
                                  output_folder=self._output_folder,
                                  out_to_in=self._out_to_in,
                                  outfile_key=None,
                                  overwrite=self._overwrite)

            converter.convert_instance(check_inputs)


class InstanceInfo(object):
    """
    Read instance info, including general problem info, shortest paths and
    nearest neighbours.
    """

    def __init__(self, instance_folder, instance_name, check_inputs=True):
        """Set the path to the instance folder, and its name from where the
        instance information can be extracted.

        Args:
            instance_folder (str): Path to the folder where the instance
                information is stored. Set as '/' if the current directory
                should be used. Typically the `output_folder` set with
                `Converter`.
            instance_name (str): Name of the instance to be extracted, typically
                the `outfile_key` set with `Converter`

        Kwargs:
            check_inputs (bool): Check inputs for obvious errors.

        TODO:
            change `instance` to file and `instance_name` to `file_name_start`.
            make a function `_pad_folder` for both classes to use.
            consider using one field with a partial file path with all but the
            extension.
        """

        self._check_inputs = check_inputs

        self._instance_folder = instance_folder
        self._instance_name = instance_name
        self._pad_folders()

        self.name = None
        self.capacity = 0
        self.maxTrip = 0
        self.dumpCost = 0
        self.nArcs = 0
        self.depotArc = 0
        self.IFarcs = []
        self.ACarcs = []
        self.beginL = {}
        self.endL = {}
        self.serveCostL = []
        self.travelCostL = []
        self.demandL = []
        self.invArcL = []
        self.sucArcL = []
        self.allIndexD = {}
        self.reqArcList = []
        self.reqArcListActual = []
        self.reqArcs_map = {}
        self.reqEdgesPure = []
        self.reqArcsPure = []
        self.reqInvArcL = []
        self.depotnewkey = None
        self.IFarcsnewkey = {}
        self.ACarcsnewkey = {}
        self.d_np_req = []
        self.if_cost_np = []
        self.nn_list = []
        self.d_full = []
        self.p_full = []

    def _check_instance_locations(self):
        """Check if instance folder exists and that it is an instance folder,
        and if any files exists corresponding to the instance name."""

        if not self._check_inputs:
            return None

        if not os.path.isdir(self._instance_folder):
            raise NotADirectoryError('`{0}` not found.'.format(
                self._instance_folder))

        folder_files = os.listdir(self._instance_folder)
        file_found = False
        for file_name in folder_files:
            if file_name.find(self._instance_name) == 0:
                file_found = True
                break

        if not file_found:
            raise FileNotFoundError('No input files found that starts '
                                    'with `{0}`.'.format(self._instance_name))

    def _pad_folders(self):
        """Pad folders so that they end with '/'"""
        if self._instance_folder is not None \
                and self._instance_folder[-1] != '/':
            self._instance_folder += '/'

    def _return_file_contents(self, extension):
        """Return the content of pickled files

        Args:
            file_path (str): path to the pickled file.
        """
        file_path = self._instance_folder + self._instance_name + extension
        with open(file_path, "rb") as file:
            return pickle.load(file)

    def set_instance_lists(self, extension='_info_lists_pickled.dat'):
        """Set all instance lists.

        Kwargs:
            extension (str): extension used to store instance lists.

        Once set, the following class attributes is available.

        .name: name of instance.

        .capacity: vehicle capacity limit.

        .maxTrip: trip duration limit of vehicle.

        .dumpCost: cost, or time of offloading waste.

        .nArcs: number of arcs in problem instance, think 2|edges|+|arcs| plus
            depot and IFs.

        .depotArc: index of depot arc.

        .IFarcs: index of intermediate facility arcs.

        .ACarcs: index of access points to graph, for example, there are only
            four roads to enter the service network with an IF outside it. With
            access points we don't need to define the network outside the
            the service area. We just need to find the shortest path cost from
            all four access points to the IF. (never used).

        .beginL: start vertex of each indexed arc.

        .endL: end vertex of each indexed arc.

        .serviceCostL: service cost of each indexed arc, zero if arc does not
            have to be serviced.

        .travelCostL: travel cost of each indexed arc. All arcs should have
            travel cost.

        .demandL: demand of each indexed arc, zero if the arc should not be
            serviced.

        .invArcL: pointer to the inverted arc index of each arc that belongs to
            an edge. points to None for pure arcs.

        .sucArcL: indices of all successor arcs for each arc, that is, arcs that
            have begin vertices equal to the end vertex of the arc. Arcs with
            no successors points Hotel California arcs, you can enter the arc
            but you may never leave.

        .allIndexD: a dictionary of all arc index to a tuple that contains the
            (begin vertex, end vertex) of the arc. Used to deconstruct a
            solution into its original vertex visitation sequence.

        .reqArcList: list of all the indices of required arcs as well as the
            depot and IFs. Used to reduce instance size only the required arcs
            are included in the solution.
        .reqArcListActual: list of all indices of only the required arcs, thus
            NOT including the depot and IFs.

        .reqArcs_map: NOT SURE

        .reqEdgesPure: indices of all required arcs that belong to an edge, NOT
            including the depot and IFs.

        .reqArcsPure: indices of all required arcs that are pure arcs, NOT
            including the depot and IFs.

        .reqInvArcL: NOT SURE

        .depotnewkey: dictionary from the depot key value to the required arc
            index value.

        .IFarcsnewkey: dictionary from the IF key value to the required arc
                index value.

        .ACarcsnewkey: dictionary from the AC key value to the required arc
                index value.
        """
        self._check_instance_locations()
        file_lists = self._return_file_contents(extension)

        (self.name,
         self.capacity,
         self.maxTrip,
         self.dumpCost,
         self.nArcs,
         self.depotArc,
         self.IFarcs,
         self.ACarcs,
         self.beginL, # begin node index of all arcs
         self.endL, # end node index of all arcs
         self.serveCostL, # service cost of all required arcs, indexed based on ???
         self.travelCostL, # travel cost of all arcs.
         self.demandL, # demand of all required arcs, indexed based on ???
         self.invArcL,
         self.sucArcL,  # direct successors of each arc (list of lists)
         self.allIndexD, # dictionary from each arc to its two vertices (combo of beginL and endL)
         self.reqArcList, # 0 to n list of required arcs.
         self.reqArcListActual, # same as reqArcList, but excludes dummy arcs.
         self.reqArcs_map, # mapping of required arc index to all arc index
         self.reqEdgesPure, # all required edges index, only one per arc combo
         self.reqArcsPure, # all required arcs index
         self.reqInvArcL, # inverse list of only required arcs, pointing to required arc index.
         self.depotnewkey, # required arc index of depot
         self.IFarcsnewkey, # required arc indices of IFs
         self.ACarcsnewkey) = file_lists

    def set_required_arc_instance_info(self, extension='_problem_info.dat'):
        """Set all required arc instance info. Info is specified for required
        arcs only, working with a dedicated arc index list which includes
        essentially dummary arcs, such as the depot and IFs. Solution
        representation requires only required arcs, with non-required arcs
        implicitly dealt with via shortest path distance matrix. The info lists
        and matrices are indexed on the required arc list, set from 1:n where
        n is the total number of required arcs, including the depot and IFs.

        Kwargs:
            extension (str): extension used to store required arc instance info.

        Once set, the following class attributes is available, where i and j
        are the indices of two required arcs, demonstrated using the Lpr-IF-c-01
        instance

        .name (str): name of instance.

            >>> info.name
            'Lpr_IF-c-01'

        .capacity (int): vehicle capacity limit.

            >>> info.capacity
            10000

        .maxTrip (int): trip duration limit of vehicle.

            >>> info.maxTrip
            28800

        .dumpCost (int): cost, or time of offloading waste.

            >>> info.dumpCost
            300

        .nArcs (int): number of arcs in problem instance, think 2|edges|+|arcs|
            plus depot and IFs.

            >>> info.nArcs
            94

        .reqArcList (list): list of all the indices of required arcs as well as
            the depot and IFs. Used to reduce instance size only the required
            arcs are included in the solution. Should be 1:n.

            >>> info.reqArcList
            [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
            55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
            89, 90, 91, 92, 93]

        .reqArcListActual (list): list of all indices of only the required arcs,
            thus NOT including the depot and IFs.

            >>> info.reqArcListActual
            [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
            55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
            89, 90, 91]

        .depotnewkey (int): depot arc index.

            >>> info.depotnewkey
            0

        .IFarcsnewkey (list): list IF arcs indices.

            >>> info.IFarcsnewkey
            [1, 2]

        .ACarcsnewkey (list): list of AC arcs indices.

        .reqEdgesPure (list): list of indices of all arcs that belong to edges,
            only one arc per edge is given.

            >>> info.reqEdgesPure
            [14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46,
            48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80,
            82, 84, 86, 88, 90]

        .reqArcsPure (list): list of indices of all arcs that belong to arc
            tasks.

            >>> info.reqArcsPure
            [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

        .reqInvArcL (list): pointer to inverse arc index of all arcs, points to
            None for pure arcs.

            For example, the inverse arc of i=20 (edge arc)
            >>> info.reqInvArcL[20]
            21

            For example, the inverse of arc i=5 (pure arc)
            >>> print(info.reqInvArcL[5])
            None

        .servceCostL (list): cost to service the required arcs.

            For example, service cost of arc i=5
            >>> info.serveCostL[5]
            427

        .demandL (list): demand of the required arcs.

            For example, demand of arc i=5
            >>> info.demandL[5]
            399

        .d_np_req (n*n matrix): shortest path cost between two required arcs.

            For example, retrieving the shortest path cost of travelling from
            arc i=5 to j=8, excluding service costs of the arcs

            >>> info.d_np_req[5][8]
            19

        .if_cost_np (n*n matrix): cost of visiting the nearest IF between two
            arcs, including offload cost.

        Example:
            For example, retrieving the cost of visiting the best IF between
            arcs i=5 and j=8:

            >>> info.if_cost_np[5][8]
            355

        .if_arc_np (n*n matrix): nearest IF to visit between two required arcs.

            For example, retrieving the best IF to visit between arcs i=5 and
            j=8:

            >>> info.if_arc_np[5][8]
            1

        """

        self._check_instance_locations()
        file_lists = self._return_file_contents(extension)

        (self.name,
         self.capacity,
         self.maxTrip,
         self.dumpCost,
         self.nArcs,
         self.reqArcList,
         self.reqArcListActual,
         self.depotnewkey,
         self.IFarcsnewkey,
         self.ACarcsnewkey,
         self.reqEdgesPure,
         self.reqArcsPure,
         self.reqInvArcL,
         self.serveCostL,
         self.demandL,
         self.d_np_req,
         self.if_cost_np,
         self.if_arc_np) = file_lists

        return None

    def set_nn_lists(self, extension='_nn_list.dat'):
        """Set the nearest neighbour lists for all required arcs.

        Kwargs:
            extension (str): extension used to store nearest-neighbour list
                info.

        Once set, the following class attribute is available:

            info.nn_list (n*n matrix): nearest neighbour list for each required
                arc with all other required arcs contained in the list, but in
                increasing order from closest to furthest arc.
        """
        self._check_instance_locations()
        self.nn_list = self._return_file_contents(extension)

    def set_sp_lists(self, extension='_sp_data_full.dat'):
        """Set the shortest path matrices for all arcs.

        Kwargs:
            extension (str): extension used to store shortest-path info.

        Once set, the following class attribute is available:

            info.d_full (n*n matrix): shortest path cost between arcs u and v.
            info.p_full (n*n matrix): direct arc before v on the shortest path
                between arcs u and v.
        """
        self._check_instance_locations()
        (self.d_full, self.p_full) = self._return_file_contents(extension)
