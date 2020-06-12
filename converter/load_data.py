# -*- coding: utf-8 -*-
"""Load and return converted input data for a problem instance. Used for the
heuristics in [1].

Currently only supports the raw input file format of Belenguer et al [2].

References:

    [1] Willemse,E.J.(2016).Heuristics for large-scale Capacitated Arc Routing
        Problems on mixed networks. PhD thesis, University of Pretoria,
        Pretoria. Available online from
        http://hdl.handle.net/2263/57510 (Last viewed on 2017-01-16).

    [2] Belenguer, J., Benavent, E., Lacomme, P., and Prins, C. (2006). Lower
        and upper bounds for the mixed capacitated arc routing problem.
        Computers & Operations Re- search, 33(12):3363--3383.

TODO:
    Error if raw input file is in incorrect format.
    Specify different input formats.
    Automatically detect input format (would be really nice).

History:
    Created on 23 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import os
import collections
from converter.input_converter import Converter
from converter.input_converter import InstanceInfo


class ConvertedInputs(object):
    """Checking and manipulating converted input data"""

    def __init__(self, file_path):
        """
        Arg:
            file_path (str): path to raw input file.
        """

        self._file_path = file_path
        self.folder_path = self.extract_folder()
        self.file_name = self.extract_striped_filename()
        self._striped_file_path = self.folder_path + self.file_name

        #  Standardised converted input data extensions
        self._input_extensions = ['_info_lists_pickled.dat',
                                  '_nn_list.dat',
                                  '_problem_info.dat',
                                  '_sp_data_full.dat']

    def extract_folder(self):
        """Extract folder path from file path
        Return:
            folder_path (str): path to folder of file.
        """
        folders = self._file_path.split('/')
        folder_path = '/'.join(folders[:-1]) + '/'

        return folder_path

    def extract_striped_filename(self):
        """Extract file name without extension from file path.

        Return:
            file_name (str): file name without an extension.
        """
        file_name_striped = self._file_path.split('/')[-1]
        file_name = '.'.join(file_name_striped.split('.')[:-1])

        return file_name

    def check_converted_input_exists(self,):
        """Check if converter input data already exists

        Raises:
            FileNotFoundError: partial converted input data found.
        """
        checks = 0
        for ext in self._input_extensions:
            check_file = self._striped_file_path + ext
            if os.path.isfile(check_file):
                print('{} found'.format(check_file))
                checks += 1
            else:
                print('{} not found'.format(check_file))

        if checks == 0:
            return False
        elif checks == len(self._input_extensions):
            return True

        raise FileNotFoundError('Some but not all converted input files exist.'
                                '\nRecommend to rerun code with '
                                '`overwrite=False`'
                                '\nso that all files can be re-generated.')

    def remove_converted_input(self):
        """Remove converted input files from file folder"""
        for ext in self._input_extensions:
            check_file = self._striped_file_path + ext
            if os.path.isfile(check_file):
                print('Removing `{0}`'.format(check_file))
                os.remove(check_file)


def load_instance(file_path, display_info=True, cache=True, overwrite=False, name_tuple=True):
    """Load problem instance info required to solve the instance and optionally
    display the solution in the format of the raw input file.

    Arg:
        file_path (str): path to raw text file, in Belenguer et al (2006)
        format.

    Kwarg:
        display_info (bool): whether the display info should be loaded. Can use
            excessive memory when solving large scale instances.
        cache (bool): if converted input data should be stored in the same
            folder as the raw input file.
        overwrite (bool): if converted input data should be overwritten if
            present in the input data folder.
        name_tuple (bool): if output should be converted to a named tuples. If this is
            the case, they can't be changed, accidently or otherwise.

    Raises:
        FileNotFoundError: raw input file not found.
        FileNotFoundError: partial converted input data found.

    Return:
        info (namedtuplec): converted input data stored as a named tuple.

        OR

        instance (class): input data as class that can be changed.
            Examples with all available fields follows:

    Fields and examples of info:

        The converted input file is loaded from a raw file as follows:

            >>> from converter import load_instance
            >>> info = load_instance('data/Lpr_IF/Lpr_IF-c-01.txt', True)

        The instance info can then be retrieved.

        info.name (str): name of instance.

            >>> info.name
            'Lpr_IF-c-01'

        info.capacity (int): vehicle capacity limit.

            >>> info.capacity
            10000

        info.maxTrip (int): trip duration limit of vehicle.

            >>> info.maxTrip
            28800

        info.dumpCost (int): cost, or time of offloading waste.

            >>> info.dumpCost
            300

        info.nArcs (int): number of arcs in problem instance, 2*|edges|+|arcs|
            + |depot| + |IFs|.

            >>> info.nArcs
            94

        info.reqArcList (list): list of all the indices of required arcs as well
            as the depot and IFs. Used to reduce instance size as only the
            required arcs are included in the solution.

            >>> info.reqArcList
            [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
            55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
            89, 90, 91, 92, 93]

            From above, 3 and 4 are not included as they belong to non-required
            arcs. Solutions returned by algorithms will consist of the indices
            of info.reqArcList. A path T=[0, 1, 2, 3, 4] therefore represents
            T_actual = [0, 1, 2, 5, 6]. The following decodes the path:

            >>> T=[0, 1, 2, 3, 4]
            >>> T_actual = [info.reqArcList[i] for i in T]
            >>> T_actual
            [0, 1, 2, 5, 6]

        info.reqArcListActual (list): list of all indices of `info.reqArcList`
            of only the required arcs, thus NOT including the depot and IFs.

            >>> len(info.reqArcList)
            92
            >>> len(info.reqArcListActual)
            89

            The above shows that there are 3 dummy arcs in the instance,
            consisting of 1 depot and 2 IFs. These are indexed at 0, 1, and 2
            and should not be in `info.reqArcListActual`

            >>> info.reqArcListActual
            [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
            55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
            89, 90, 91]

            As shown, they are correctly not included in the list.

            >>> info.reqArcList[info.reqArcListActual[-1]]
            93

        info.depotnewkey (int): depot arc index. This is based on
            info.reqArcList indices.

            >>> info.depotnewkey
            0

        info.IFarcsnewkey (list): list IF arcs indices. This is based on
            info.reqArcList indices.

            >>> info.IFarcsnewkey
            [1, 2]

        info.ACarcsnewkey (list): list of AC arcs indices. This is based on
            info.reqArcList indices.

            >>> info.ACarcsnewkey
            []

        info.reqEdgesPure (list): list of indices of all arcs that belong to
            edges, only one arc per edge is given.

            >>> info.reqEdgesPure
            [14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46,
            48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80,
            82, 84, 86, 88, 90]

        info.reqArcsPure (list): list of indices of all arcs that belong to arc
            tasks.

            >>> info.reqArcsPure
            [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

        info.reqInvArcList (list): pointer to inverse arc index of all arcs,
            points to None for pure arcs.

            For example, the inverse arc of i=20 (edge arc)
            >>> info.reqInvArcL[20]
            21

            For example, the inverse of arc i=5 (pure arc)
            >>> print(info.reqInvArcL[5])
            None

        info.serveCostL (list): cost to service the required arcs.

            For example, service cost of arc i=5
            >>> info.serveCostL[5]
            427

        info.demandL (list): demand of the required arcs.

            For example, demand of arc i=5
            >>> info.demandL[5]
            399

        info.d (n*n matrix): shortest path cost between two required arcs.

            For example, retrieving the shortest path cost of travelling from
            arc i=5 to j=8, excluding service costs of the arcs

            >>> info.d_np_req[5][8]
            19

        info.if_cost_np (n*n matrix): cost of visiting the nearest IF between two
            arcs, including offload cost.

            For example, retrieving the cost of visiting the best IF between
            arcs i=5 and j=8:

            >>> info.if_cost_np[5][8]
            355

        info.if_arc_np (n*n matrix): nearest IF to visit between two required
        arcs.

            For example, retrieving the best IF to visit between arcs i=5 and
            j=8:

            >>> info.if_arc_np[5][8]
            1

        info.nn_list (n*n matrix): nearest neighbour list for each required arc
            with all other required arcs contained in the list, but in
            increasing order from closest to furthest arc.

            For example, retrieving the 10 nearest arcs to arc i=10:

            >>> info.nn_list[5][:10]
            [69, 74, 55, 5, 72, 9, 10, 88, 13, 12]

        info.reqArcs_map (list): list of the required arc indices back to the
            full arc index list.

            >>> info.reqArcs_map[5]
            5

            Convention is that the first entries in the raw text files are the
            required arcs, therefore a one-to-one mapping often exists between
            required arcs and their indices among all arcs. This may not always
            be the case.

        info.allIndexD (dict): arc index to start and end vertex tuple mapping.

            >>> info.allIndexD[5]
            (9, 4)

            Arc index 5 represent arc (9, 4), starting at vertex 9 and ending at
            vertex 4.

        info.travelCostL (list): cost of only traversing arc u without service,
            defined for the full arc list. Only really used for solution
            display purposes as traversal time is catered for via info.d_full

            >>> len(info.travelCostL)
            94
            >>> info.travelCostL[5]
            >>> 22

        info.d_full (n*n matrix): shortest path cost between arcs u and v for
            all arcs, not just required arcs. Required arcs have to be mapped
            back using `reqArcs_map` to retrieve the correct cost between
            required arcs.

            >>> len(info.reqArcs_map)
            92
            >>> len(info.d_full)
            94

            There are 92 required arcs and 94 arcs in total. There are therefore
            two non-required arcs. This can be confirmed by inspecting the raw
            input data file. The shortest path cost between arcs 5 and 93:

            >>> info.d_full[5][93]
            113

        info.p_full (n*n matrix): predecessor arc before v on the shortest path
            between arcs u and v.

            >>> info.p_full[5][93]
            86

            The arc to traverse right before 93 on the shortest path between
            arcs 5 and 93 is 86. To retrieve the full shortest path, call
            v(i) = info.p_full[5][v(i-1)], incrementing i after each call until
            v(i)=5.
    """

    #  Object for manipulating converted input files.
    inputs = ConvertedInputs(file_path)

    if not os.path.isfile(file_path):
        raise FileNotFoundError('`{0}` not found'.format(file_path))

    if overwrite or not inputs.check_converted_input_exists():
        #  Object for creating and storing converted input data.
        conv = Converter(file_path, out_to_in=True, overwrite=overwrite)
        conv.convert_instance()
        print('Saving converted data files to `{0}`'.format(inputs.folder_path))
    else:
        print('Converted input data exist in `{0}`, proceeding to load '
              'data\n'.format(inputs.folder_path))

    #  Object of retrieving stored converted input data
    instance = InstanceInfo(instance_folder=inputs.folder_path,
                            instance_name=inputs.file_name)

    if display_info is True:
        instance.set_sp_lists('_sp_data_full.dat')
        instance.set_instance_lists('_info_lists_pickled.dat')

    instance.set_required_arc_instance_info('_problem_info.dat')
    instance.set_nn_lists('_nn_list.dat')

    if not name_tuple:
        instance.d = instance.d_np_req
        instance.reqInvArcList = instance.reqInvArcL
        return instance

    #  Converted input data is assigned to a named tuple
    Info = collections.namedtuple('info', 'name '
                                          'capacity '
                                          'maxTrip '
                                          'dumpCost '
                                          'nArcs '
                                          'reqArcList '
                                          'reqArcListActual '
                                          'depotnewkey '
                                          'IFarcsnewkey '
                                          'ACarcsnewkey '
                                          'reqEdgesPure '
                                          'reqArcsPure '
                                          'reqInvArcList '
                                          'serveCostL '
                                          'demandL '
                                          'd '
                                          'if_cost_np '
                                          'if_arc_np '
                                          'nn_list '
                                          'reqArcs_map '
                                          'allIndexD '
                                          'travelCostL '
                                          'd_full '
                                          'p_full ')

    info = Info(name=instance.name,
                capacity=instance.capacity,
                maxTrip=instance.maxTrip,
                dumpCost=instance.dumpCost,
                nArcs=instance.nArcs,
                reqArcList=instance.reqArcList,
                reqArcListActual=instance.reqArcListActual,
                depotnewkey=instance.depotnewkey,
                IFarcsnewkey=instance.IFarcsnewkey,
                ACarcsnewkey=instance.ACarcsnewkey,
                reqEdgesPure=instance.reqEdgesPure,
                reqArcsPure=instance.reqArcsPure,
                reqInvArcList=instance.reqInvArcL,
                serveCostL=instance.serveCostL,
                demandL=instance.demandL,
                d=instance.d_np_req,
                if_cost_np=instance.if_cost_np,
                if_arc_np=instance.if_arc_np,
                nn_list=instance.nn_list,
                reqArcs_map=instance.reqArcs_map,
                allIndexD=instance.allIndexD,
                travelCostL=instance.travelCostL,
                d_full=instance.d_full,
                p_full=instance.p_full)

    if not cache:
        #  Remove converted input data files
        inputs.remove_converted_input()

    return info
