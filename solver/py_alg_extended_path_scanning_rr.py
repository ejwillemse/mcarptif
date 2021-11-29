# Generate starting solutions using the extended path scanning heuristic
# Creator: Elias Willemse (ejwillemse@gmail.com)
#
# Derived from the article:
# Belenguer, J., Benavent, E., Lacomme, P., Prins, C. (2006). Lower and uper
# bounds for the mixed capacitated arc routing problem. Computers & Operations
# Research. 33(12)
# p. 3363-3383.
# Specifically pages 3369-3370.
from __future__ import division
import numpy as np
import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()})

import solver.evaluatesolutions as evaluatesolutions

from copy import deepcopy
from math import ceil

from solver.py_solution_test import test_solution  # From Dev_SolutionOperators
import solver.py_solution_stats as py_solution_stats
import solver.c_alg_extended_path_scanning_rr as c_alg_extended_path_scanning

from converter.py_return_problem_data import return_problem_data  # From Dev_TestData
import solver.py_solution_builders as build_solution
import cProfile
import os

from solver.py_reduce_number_trips import Reduce_Trips

from time import perf_counter as clock
from solver.py_display_solution import display_solution_stats

huge = 1e300000
HUGE = 1e300000


def populate_c_local_search(info, full=False):
    c_alg_extended_path_scanning.set_input(info, full)


def free_c_local_search(full=False):
    c_alg_extended_path_scanning.free_input(full)


class TieBreakRules(object):
    """
    Break ties if multiple arcs are close together. Rules are used
    for CLARPIF and CARP.
    """

    def __init__(self):
        self.cost_limit_frac = 0.8

    def maxdepot(self, nearestArcsL):
        """
        Find arc that will take the trip furthest to depot after service.
        """
        bestdist = -1
        for arc in nearestArcsL:
            dist_to_depot = self.d[arc][self.end_depot]
            if dist_to_depot > bestdist:
                bestdist = dist_to_depot
                arc_return = arc
        return arc_return

    def mindepot(self, nearestArcsL):
        """
        Find arc that will take the trip closest to depot after service.
        """
        bestdist = huge
        for arc in nearestArcsL:
            dist_to_depot = self.d[arc][self.end_depot]
            if dist_to_depot < bestdist:
                bestdist = dist_to_depot
                arc_return = arc
        return arc_return

    def maxIFdepot(self, nearestArcsL):
        """
        Find arc that will take the trip furthest from IF and then depot visit (last visit in route).
        """
        bestdist = -1
        for arc in nearestArcsL:
            dist_to_if = self.if_cost[arc][self.end_depot]
            if dist_to_if > bestdist:
                bestdist = dist_to_if
                arc_return = arc
        return arc_return

    def minIFdepot(self, nearestArcsL):
        """
        Find arc that will take the trip closest to IF and then depot visit (last visit in route).
        """
        bestdist = huge
        for arc in nearestArcsL:
            dist_to_if = self.if_cost[arc][self.end_depot]
            if dist_to_if < bestdist:
                bestdist = dist_to_if
                arc_return = arc
        return arc_return

    def maxIF(self, nearestArcsL):
        """
        Find arc that will take the trip furthest from an IF.
        """
        bestdist = -1
        for arc in nearestArcsL:
            dist_to_if = self.if_cost[arc][arc]
            if dist_to_if > bestdist:
                bestdist = dist_to_if
                arc_return = arc
        return arc_return

    def minIF(self, nearestArcsL):
        """
        Find arc that will take the trip closest to an IF.
        """
        bestdist = huge
        for arc in nearestArcsL:
            dist_to_if = self.if_cost[arc][arc]
            if dist_to_if < bestdist:
                bestdist = dist_to_if
                arc_return = arc
        return arc_return

    def maxyield(self, nearestArcsL):
        """
        Find arc with highest demand:cost-to-service (productivity).
        """
        bestyield = -1
        for arc in nearestArcsL:
            if self.serveCost[arc] == 0:
                self.serveCost[arc] = 1
                # raise NameError('Arc has a service cost of 0')
                # arcyield = 1e30000
            arcyield = float(self.demand[arc]) / float(self.serveCost[arc])
            if arcyield > bestyield:
                bestyield = arcyield
                arc_return = arc
        return arc_return

    def minyield(self, nearestArcsL):
        """
        Find arc with lowest demand:cost-to-service (productivity).
        """
        bestyield = huge
        for arc in nearestArcsL:
            if self.serveCost[arc] == 0:
                self.serveCost[arc] = 1
                # raise NameError('Arc has a service cost of 0')
                # arcyield = 1e30000
            arcyield = float(self.demand[arc]) / float(self.serveCost[arc])
            if arcyield < bestyield:
                bestyield = arcyield
                arc_return = arc
        return arc_return

    def hybrid(self, nearestArcsL, vehicleSubTripLoad):
        """
        If trip is half full, use mindepo rule, else use maxdepo rule.
        """
        if vehicleSubTripLoad <= float(self.capacity) / 2:
            return self.maxdepot(nearestArcsL)
        else:
            return self.mindepot(nearestArcsL)

    def hybridIF(self, nearestArcsL, vehicleSubTripLoad):
        """
        If trip is half full, use minIF rule, else use maxIF rule.
        """
        if vehicleSubTripLoad <= float(self.capacity) / 2:
            return self.maxIF(nearestArcsL)
        else:
            return self.minIF(nearestArcsL)

    def hybridIFdepot(self, nearestArcsL, vehicleSubTripLoad, vehicleCost):
        """
        If route is close (specified fraction) to maxtrip limit, use minIFdepot rule, else use hybirdIF rule.
        """
        if vehicleCost >= self.cost_limit_frac * self.maxTrip:
            return self.minIFdepot(nearestArcsL)
        else:
            return self.hybridIF(nearestArcsL, vehicleSubTripLoad)

    def randomrule(self, nearestArcsL, vehicleSubTripLoad):
        """
        Randomly use any of the five classic rules: maxdepo, mindepo, maxyield, minyield, hybrid.
        """
        if vehicleSubTripLoad == None:
            rulen = np.random.randint(1, 5)
        else:
            rulen = np.random.randint(1, 6)
        if rulen == 1:
            return self.maxdepot(nearestArcsL)
        if rulen == 2:
            return self.mindepot(nearestArcsL)
        if rulen == 3:
            return self.maxyield(nearestArcsL)
        if rulen == 4:
            return self.minyield(nearestArcsL)
        if rulen == 5:
            return self.hybrid(nearestArcsL, vehicleSubTripLoad)

    def randomruleIFs_sub(self, nearestArcsL, vehicleSubTripLoad, vehicleCost):
        """
        Randomly use any of the five IF rules: maxIF, minIF, maxyield, minyield, hybridIFdepot.
        """
        if vehicleSubTripLoad == None:
            rulen = np.random.randint(1, 5)
        else:
            rulen = np.random.randint(1, 6)
        if rulen == 1:
            return self.maxIF(nearestArcsL)
        if rulen == 2:
            return self.minIF(nearestArcsL)
        if rulen == 3:
            return self.maxyield(nearestArcsL)
        if rulen == 4:
            return self.minyield(nearestArcsL)
        if rulen == 5:
            return self.hybridIFdepot(nearestArcsL, vehicleSubTripLoad, vehicleCost)

    def randomruleIFs(self, nearestArcsL, vehicleSubTripLoad, vehicleCost):
        """
        Randomly use any of the five IF rules: maxIF, minIF, maxyield, minyield, hybridIFdepot.
        """
        if vehicleSubTripLoad == None:
            rulen = np.random.randint(1, 5)
        else:
            rulen = np.random.randint(1, 6)
        if rulen == 1:
            return self.maxIF(nearestArcsL)
        if rulen == 2:
            return self.minIF(nearestArcsL)
        if rulen == 3:
            return self.maxyield(nearestArcsL)
        if rulen == 4:
            return self.minyield(nearestArcsL)
        if rulen == 5:
            return self.hybridIFdepot(nearestArcsL, vehicleSubTripLoad, vehicleCost)

    def randomruleAll(self, nearestArcsL, vehicleSubTripLoad, vehicleCost):
        """
        Randomly use any of the eight rules, classic and normal.
        """
        if vehicleSubTripLoad == None:
            rulen = np.random.randint(1, 8)
        else:
            rulen = np.random.randint(1, 9)
        if rulen == 1:
            return self.maxdepot(nearestArcsL)
        if rulen == 2:
            return self.mindepot(nearestArcsL)
        if rulen == 3:
            return self.maxIF(nearestArcsL)
        if rulen == 4:
            return self.minIF(nearestArcsL)
        if rulen == 5:
            return self.maxyield(nearestArcsL)
        if rulen == 6:
            return self.minyield(nearestArcsL)
        if rulen == 7:
            return self.hybrid(nearestArcsL, vehicleSubTripLoad)
        if rulen == 8:
            return self.hybridIFdepot(nearestArcsL, vehicleSubTripLoad, vehicleCost)

    def randomarc(self, nearestArcsL):
        """
        Randomly choose an arc.
        """
        arcnumber = np.random.randint(0, len(nearestArcsL))
        return nearestArcsL[arcnumber]

    def choose_arc(self, nearestArcsL, vehicleSubTripLoad, vehicleCost, rule="MaxDepo"):
        """
        Use case for rule specified.
        """
        if rule == "MaxDepo":
            return self.maxdepot(nearestArcsL)
        if rule == "MinDepo":
            return self.mindepot(nearestArcsL)
        if rule == "MaxIF":
            return self.maxIF(nearestArcsL)
        if rule == "MinIF":
            return self.minIF(nearestArcsL)
        if rule == "MaxYield":
            return self.maxyield(nearestArcsL)
        if rule == "MinYield":
            return self.minyield(nearestArcsL)

        if rule == "Hybrid":
            return self.hybrid(nearestArcsL, vehicleSubTripLoad)
        if rule == "HybridIFdepto":
            return self.hybridIFdepot(nearestArcsL, vehicleSubTripLoad, vehicleCost)

        if rule == "RandomRule":
            return self.randomrule(nearestArcsL, vehicleSubTripLoad)
        if rule == "RandomRuleIFs":
            return self.randomruleIFs(nearestArcsL, vehicleSubTripLoad, vehicleCost)
        if rule == "RandomRuleAll":
            return self.randomruleAll(nearestArcsL, vehicleSubTripLoad, vehicleCost)
        if rule == "RandomArc":
            return self.randomarc(nearestArcsL)


class ExtendedPathScanning_Operators(object):
    """
    Basic Path Scanning Operators used with both the CARP and CLARPIF.
    """

    def testload(self, arc):
        """
        Test if an arc can be added without exceeding vehicle capacity.
        """
        if (self.tripload + self.demand[arc]) <= self.capacity:
            return True
        else:
            return False

    def testtriplimit(self, arc, arcdist):
        """
        Test if an arc can be added without exceeding max trip length.
        """
        if (
            self.routecost
            + arcdist
            + self.serveCost[arc]
            + self.if_cost[arc][self.end_depot]
        ) <= self.maxTrip:
            return True
        else:
            return False

    def testtriplimit_est(self, arc, arcdist, estimate_if_cost):
        """
        Test if an arc can be added without exceeding max trip length.
        """
        if (
            self.routecost
            + arcdist
            + self.serveCost[arc]
            + self.if_cost[arc][self.end_depot]
            + estimate_if_cost
        ) <= self.maxTrip:
            return True
        else:
            return False

    def c_findnearestarcs(self, previousarc):
        (nearestarcs, nearest) = c_alg_extended_path_scanning.findnearestarcs(
            previousarc, self.reqArcsUnassigned, self.tripload, self.routecost
        )
        return (nearestarcs, nearest)

    def c_findnearestarcs_elipse(self, previousarc):
        (nearestarcs, nearest, k) = c_alg_extended_path_scanning.findnearestarcs_elipse(
            previousarc,
            self.reqArcsUnassigned,
            self.tripload,
            self.routecost,
            self._tc,
            self._ned,
        )
        return (nearestarcs, nearest, k)

    def findnearestarcs(self, previousarc):
        """
        Find the nearest servisable arc, while taking
        into account load and maxtrip restrictions.
        """
        nearest = huge
        nearestarcs = []

        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]

            if disttoarc <= nearest:

                loadflag = self.testload(nextarc)
                triplimitflag = self.testtriplimit(nextarc, disttoarc)

                if (loadflag == True) & (triplimitflag == True):
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    elif disttoarc == nearest:
                        nearestarcs.append(nextarc)

        return (nearestarcs, nearest)

    def findnearestarcs_elipse(self, previousarc):
        """
        Find the nearest servisable arc, while taking
        into account load and maxtrip restrictions.
        """
        nearest = huge
        nearestarcs = []
        disttodepot_direct = self.if_cost[previousarc][self.depot]
        k = 0
        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]
            serveC = self.serveCost[nextarc]
            disttodepot = self.if_cost[nextarc][self.depot]
            if (disttoarc + serveC + disttodepot) <= (
                self._tc / self._ned + disttodepot_direct
            ):
                k += 1
                if disttoarc <= nearest:
                    loadflag = self.testload(nextarc)
                    triplimitflag = self.testtriplimit(nextarc, disttoarc)
                    if (loadflag == True) & (triplimitflag == True):
                        if disttoarc < nearest:
                            nearest = disttoarc
                            nearestarcs = [nextarc]
                        elif disttoarc == nearest:
                            nearestarcs.append(nextarc)
        # print('Available before after',self._ned_left,k,k/self._ned_left)
        return (nearestarcs, nearest, k)

    def findnearestarcs_cap_elipse(self, previousarc):
        """
        Find the nearest servisable arc, while taking
        into account load and maxtrip restrictions.
        """
        nearest = huge
        nearestarcs = []
        disttodepot_direct = 1e300000
        if_k = None
        for i in self.info.IFarcsnewkey:
            if self.d[previousarc][i] < disttodepot_direct:
                if_k = i
                disttodepot_direct = self.d[previousarc][i]
        k = 0
        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]
            serveC = self.serveCost[nextarc]
            disttodepot = self.d[nextarc][if_k]
            if (disttoarc + serveC + disttodepot) <= (
                self._tc / self._ned + disttodepot_direct
            ):
                k += 1
                if disttoarc <= nearest:
                    loadflag = self.testload(nextarc)
                    triplimitflag = self.testtriplimit(nextarc, disttoarc)
                    if (loadflag == True) & (triplimitflag == True):
                        if disttoarc < nearest:
                            nearest = disttoarc
                            nearestarcs = [nextarc]
                        elif disttoarc == nearest:
                            nearestarcs.append(nextarc)
        # print('Available before after',self._ned_left,k,k/self._ned_left)
        return (nearestarcs, nearest, k)

    def c_findnearestarcs_cap_elipse(self, previousarc):
        (
            nearestarcs,
            nearest,
            k,
        ) = c_alg_extended_path_scanning.findnearestarcs_cap_elipse(
            previousarc,
            self.reqArcsUnassigned,
            self.tripload,
            self.routecost,
            self._tc,
            self._ned,
            self.info.IFarcsnewkey,
        )
        return (nearestarcs, nearest, k)

    def c_findnearestarcs_noload(self, previousarc, estimate_if_cost):
        (nearestarcs, nearest) = c_alg_extended_path_scanning.findnearestarcs_noload(
            previousarc,
            self.reqArcsUnassigned,
            self.tripload,
            self.routecost,
            estimate_if_cost,
        )
        return (nearestarcs, nearest)

    def findnearestarcs_noload(self, previousarc, estimate_if_cost):
        """
        Find the nearest servisable arc, while taking
        into account load and maxtrip restrictions.
        """
        nearest = huge
        nearestarcs = []

        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]

            if disttoarc <= nearest:
                triplimitflag = self.testtriplimit_est(
                    nextarc, disttoarc, estimate_if_cost
                )
                if triplimitflag:
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    elif disttoarc == nearest:
                        nearestarcs.append(nextarc)
        return (nearestarcs, nearest)

    def c_findnearestIFarcs(self, previousarc):
        (nearestarcs, nearest) = c_alg_extended_path_scanning.findnearestIFarcs(
            previousarc, self.reqArcsUnassigned, self.tripload, self.routecost
        )

        return (nearestarcs, nearest)

    def c_findnearestIFarcs_elipse(self, previousarc):
        (
            nearestarcs,
            nearest,
            k,
        ) = c_alg_extended_path_scanning.findnearestIFarcs_elipse(
            previousarc,
            self.reqArcsUnassigned,
            self.tripload,
            self.routecost,
            self._tc,
            self._ned,
            self.inc_frac,
        )

        return (nearestarcs, nearest, k)

    def findnearestIFarcs(self, previousarc):
        """
        Find the nearest servisable arc that can be serviced after
        visiting a dumpsite while taking maxtrip restriction into account
        """
        nearest = huge
        nearestarcs = []

        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.if_cost[previousarc][nextarc]
            if disttoarc <= nearest:

                triplimitflag = self.testtriplimit(nextarc, disttoarc)
                if triplimitflag:
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    elif disttoarc == nearest:
                        nearestarcs.append(nextarc)

        return (nearestarcs, nearest)

    def findnearestIFarcs_elipse(self, previousarc):
        """
        Find the nearest servisable arc that can be serviced after
        visiting a dumpsite while taking maxtrip restriction into account
        """
        nearest = huge
        nearestarcs = []
        disttodepot_direct = self.if_cost[previousarc][self.depot]
        k = 0
        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.if_cost[previousarc][nextarc]
            disttodepot = self.if_cost[nextarc][self.depot]
            serveC = self.serveCost[nextarc]
            if (disttoarc + serveC + disttodepot) <= 1.5 * (
                self._tc / self._ned + disttodepot_direct
            ):
                k += 1
                if disttoarc <= nearest:
                    triplimitflag = self.testtriplimit(nextarc, disttoarc)
                    if triplimitflag:
                        if disttoarc < nearest:
                            nearest = disttoarc
                            nearestarcs = [nextarc]
                        elif disttoarc == nearest:
                            nearestarcs.append(nextarc)
        # print('Available before after IF',self._ned_left,k,k/self._ned_left)
        return (nearestarcs, nearest, k)

    def findnearestarcs_nolimit(self, previousarc):
        """
        Find nearest servisable arc while only taking capacity into consideration.
        Used with classical CARP.
        """
        nearest = huge
        nearestarcs = []
        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]
            if disttoarc <= nearest:
                if self.testload(nextarc):
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    else:
                        nearestarcs.append(nextarc)
        return (nearestarcs, nearest)

    def findnearestarcs_nolimit_elipse(self, previousarc):
        """
        Find nearest servisable arc while only taking capacity and elipse rule into consideration.
        Used with classical CARP.
        """
        nearest = huge
        nearestarcs = []
        disttodepot_direct = self.d[previousarc][self.depot]
        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]
            disttodepot = self.d[nextarc][self.depot]
            serveC = self.serveCost[nextarc]
            if (disttoarc + serveC + disttodepot) <= (
                self._tc / self._ned + disttodepot_direct
            ):
                if disttoarc <= nearest:
                    loadflag = self.testload(nextarc)
                    if loadflag == True:
                        if disttoarc < nearest:
                            nearest = disttoarc
                            nearestarcs = [nextarc]
                        elif disttoarc == nearest:
                            nearestarcs.append(nextarc)

        return (nearestarcs, nearest)

    def c_findnearestarcs_nolimit(self, previousarc):
        (nearestarcs, nearest) = c_alg_extended_path_scanning.findnearestarcs_nolimit(
            previousarc, self.reqArcsUnassigned, self.tripload
        )
        return (nearestarcs, nearest)

    def c_findnearestarcs_nolimit_elipse(self, previousarc):
        (
            nearestarcs,
            nearest,
            k,
        ) = c_alg_extended_path_scanning.findnearestarcs_nolimit_elipse(
            previousarc, self.reqArcsUnassigned, self.tripload, self._tc, self._ned
        )
        return (nearestarcs, nearest, k)

    def c_findnearestarcsbalanced_sub1(self, previousarc):
        (nearestarcs, nearest) = c_alg_extended_path_scanning.findnearestarcs_sub1(
            previousarc, self.reqArcsUnassigned
        )
        return (nearestarcs, nearest)

    def findnearestarcsbalanced_sub1(self, previousarc):
        """
        Find nearest arc without taking capacity and maxtrip into consideration.
        """
        nearest = huge
        nearestarcs = []
        for nextarc in self.reqArcsUnassigned:
            disttoarc = self.d[previousarc][nextarc]
            if disttoarc < nearest:
                nearest = disttoarc
                nearestarcs = [nextarc]
            elif disttoarc == nearest:
                nearestarcs.append(nextarc)
        return (nearestarcs, nearest)

    def c_checknearestarcs(self, nearestarcs, nearest):
        nextarcfine = c_alg_extended_path_scanning.checknearestarcs(
            nearestarcs, nearest, self.tripload, self.routecost
        )
        return nextarcfine

    def checknearestarcs(self, nearestarcs, nearest):
        """
        Check which nearest arcs does not exceed capacity and maxtrip restrictions.
        """
        nextarcfine = []
        for arc in nearestarcs:
            if (self.testload(arc) == True) & (
                self.testtriplimit(arc, nearest) == True
            ):
                nextarcfine.append(arc)
        return nextarcfine

    def c_checknearestarcs_noload(self, nearestarcs, nearest, estimate_if_cost):
        """
        Check which nearest arcs does not exceed capacity and maxtrip restrictions.
        """
        nextarcfine = c_alg_extended_path_scanning.checknearestarcs_noload(
            nearestarcs, nearest, self.tripload, self.routecost, estimate_if_cost
        )
        return nextarcfine

    def checknearestarcs_noload(self, nearestarcs, nearest, estimate_if_cost):
        """
        Check which nearest arcs does not exceed capacity and maxtrip restrictions.
        """
        nextarcfine = []
        for arc in nearestarcs:
            if self.testtriplimit_est(arc, nearest, estimate_if_cost):
                nextarcfine.append(arc)
        return nextarcfine

    def checknearestarcs_nolimits(self, nearestarcs):
        """
        Check which nearest arcs does not exceed capacity. Used with CARP.
        """
        nextarcfine = []
        for arc in nearestarcs:
            if self.testload(arc):
                nextarcfine.append(arc)
        return nextarcfine

    def findnearestarcsbalanced(self, previousarc):
        """
        Find nearest arcs, and then limits arcs to those that adhere to
        capacity and maxtrip restrictions. If none is found, the trip
        is closed.
        """
        if self.c_modules:
            (nearestarcs, nearest) = self.c_findnearestarcsbalanced_sub1(previousarc)
            nearestarcs = self.c_checknearestarcs(nearestarcs, nearest)
        else:
            (nearestarcs, nearest) = self.findnearestarcsbalanced_sub1(previousarc)
            nearestarcs = self.checknearestarcs(nearestarcs, nearest)
        return (nearestarcs, nearest)

    def findnearestarcsbalanced_noload(self, previousarc, estimate_if_cost):
        """
        Find nearest arcs, and then limits arcs to those that adhere to
        capacity and maxtrip restrictions. If none is found, the trip
        is closed.
        """
        if self.c_modules:
            (nearestarcs, nearest) = self.c_findnearestarcsbalanced_sub1(previousarc)
            nearestarcs = self.c_checknearestarcs_noload(
                nearestarcs, nearest, estimate_if_cost
            )
        else:
            (nearestarcs, nearest) = self.findnearestarcsbalanced_sub1(previousarc)
            nearestarcs = self.checknearestarcs_noload(
                nearestarcs, nearest, estimate_if_cost
            )
        return (nearestarcs, nearest)

    def findnearestarcsbalanced_nolimit(self, previousarc):
        """
        Find nearest arcs, and then limits arcs to those that adhere to
        capacity restrictions. If none is found, the route is closed. Used
        with classical CARP.
        """
        if self.c_modules:
            (nearestarcs, nearest) = self.findnearestarcsbalanced_sub1(previousarc)
        else:
            (nearestarcs, nearest) = self.c_findnearestarcsbalanced_sub1(previousarc)
        nearestarcs = self.checknearestarcs_nolimits(nearestarcs)
        return (nearestarcs, nearest)

    def resetIncumbent(self):
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehComp = {}

    def updateIncumbent(self, solution):
        if solution["TotalCost"] < self.bestSol:
            self.bestSol = solution["TotalCost"]
            self.bestSolN = solution["nVehicles"]
            self.bestSolComp = deepcopy(solution)
        if solution["nVehicles"] < self.bestVehN:
            self.bestVeh = solution["TotalCost"]
            self.bestVehN = solution["nVehicles"]
            self.bestVehComp = deepcopy(solution)
        elif (solution["nVehicles"] == self.bestVehN) & (
            solution["TotalCost"] < self.bestVeh
        ):
            self.bestVeh = solution["TotalCost"]
            self.bestVehN = solution["nVehicles"]
            self.bestVehComp = deepcopy(solution)


class EPS(ExtendedPathScanning_Operators, TieBreakRules):
    """
    Build solution using Extended Path Scanning. Algorithm finds
    closest unserviced arc and use rules to break ties. Different rules
    yield different solutions, where the best one can be returned.

    To use the ExtendedPathScanning_Operators definitions, routes are
    treated as trips, with one trip per vehicle.
    """

    def __init__(self, info):
        TieBreakRules.__init__(self)
        self.capacity = info.capacity
        self.dumpCost = info.dumpCost
        self.reqArcs = list(info.reqArcListActual())  # TODO: decide between
        # numpy and python
        self.depot = info.depotnewkey
        self.end_depot = self.depot
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.rule = "MaxDepo"
        self.classic_rules = ["MaxDepo", "MinDepo", "MaxYield", "MinYield", "Hybrid"]
        self.testsolutions = False
        self.info = info
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehN = {}
        self.c_modules = False
        self.disp = display_solution_stats(info)
        self.break_even_point = 1e300000
        self.break_even_iter_limit = 100
        self.Reduce_Trips = Reduce_Trips(info)
        self.reduce_all_trips = True
        self.reduce_best_trips = True
        self.elipse_rule = False
        self.elipse_alpha = 1.5
        self.print_iter = 1
        self._got_to_scan = []
        self.elipse_forced = 0
        self.nRoutesLB = 0
        self._allSolutions = []
        self._saveSolutions = False
        self._allFullSolutions = []
        self._allSolutionsTime = []

    def _calc_elipse_input(self):
        ned = 0
        td = 0
        tc = 0
        arc_added = self.info.reqArcList[:]
        for arc in self.reqArcs:
            if arc_added[arc] != None:
                ned += 1
                td += self.demand[arc]
                tc += self.serveCost[arc]
                if self.invArcList[arc] != None:
                    arc_added[self.invArcList[arc]] = None
        self._ned = ned
        self._ned_left = ned
        self._td = td
        self._tc = tc

    def addarc(self, arc, nearest, trip):
        """
        Add arc to trip and update all cost and load info.
        """

        self.totalcost += self.serveCost[arc] + nearest
        self.tripcost += self.serveCost[arc] + nearest
        self.tripdeadhead += nearest
        self.tripload += self.demand[arc]
        self.tripservicecosts += self.serveCost[arc]

        arc1 = self.reqArcsUnassigned.index(arc)
        if self.invArcList[arc]:
            arc2 = self.reqArcsUnassigned.index(self.invArcList[arc])
            del self.reqArcsUnassigned[max(arc1, arc2)]
            del self.reqArcsUnassigned[min(arc1, arc2)]
        else:
            del self.reqArcsUnassigned[arc1]

        # self._ned_left -= 1
        trip.append(arc)
        return trip

    def addDepotArc(self, trip):
        """
        Close route by adding a IF then depot visit.
        """
        dumpvisit_cost = self.d[trip[-1]][self.end_depot] + self.dumpCost
        self.totalcost += dumpvisit_cost
        self.tripcost += dumpvisit_cost
        self.tripdeadhead += dumpvisit_cost
        trip.append(self.end_depot)
        return trip

    def reset_trip(self):
        self.tripload = 0
        self.tripcost = 0
        self.tripdeadhead = 0
        self.tripservicecosts = 0

    def _check_elipse_rule(self, tripload):
        if self.elipse_rule:
            if (self.capacity - tripload) <= (self.elipse_alpha * self._td / self._ned):
                # print('Elipse True',self.capacity,tripload,self.capacity - tripload)
                return True
            else:
                # print('Elipse False',self.capacity,tripload,self.capacity - tripload)
                return False
        else:
            return False

    def buildroute(self):
        """
        Build route by finding the closest unserviced arc. Arc is added
        to a trip if it doesn't exceed vehicle capacity.
        IF a route is full, a depot visit is added.
        """
        self.reset_trip()
        trip = [self.depot]

        while True:
            previousarc = trip[-1]
            if self.c_modules:
                if self._check_elipse_rule(self.tripload):
                    (nearestarcs, nearest, k) = self.c_findnearestarcs_nolimit_elipse(
                        previousarc
                    )
                else:
                    (nearestarcs, nearest) = self.c_findnearestarcs_nolimit(previousarc)
            else:
                if self._check_elipse_rule(self.tripload):
                    (nearestarcs, nearest, k) = self.findnearestarcs_nolimit_elipse(
                        previousarc
                    )
                else:
                    (nearestarcs, nearest) = self.findnearestarcs_nolimit(previousarc)
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                vehicleCost = 0
                chosearc = self.choose_arc(
                    nearestarcs, self.tripload, vehicleCost, self.rule
                )
                trip = self.addarc(chosearc, nearest, trip)
            else:  # trip is full
                trip = self.addDepotArc(trip)
                self.routeTripsLists = deepcopy(trip)
                break
            if not self.reqArcsUnassigned:
                trip = self.addDepotArc(trip)
                self.routeTripsLists = deepcopy(trip)
                break

    def buildbalancedroute(self):
        """
        Build route by finding the closest unserviced arc. Arc is added
        to a trip if it doesn't exceed vehicle capacity.
        IF a route is full, a depot visit is added.
        """
        self.reset_trip()
        trip = [self.depot]

        while True:
            previousarc = trip[-1]
            (nearestarcs, nearest) = self.findnearestarcsbalanced_nolimit(previousarc)
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                vehicleCost = 0
                chosearc = self.choose_arc(
                    nearestarcs, self.tripload, vehicleCost, self.rule
                )
                trip = self.addarc(chosearc, nearest, trip)
            elif len(trip) == 1:
                if self.c_modules:
                    (nearestarcs, nearest) = self.c_findnearestarcs_nolimit(previousarc)
                else:
                    (nearestarcs, nearest) = self.findnearestarcs_nolimit(previousarc)
                if (
                    len(nearestarcs) == 1
                ):  # Arc can be added without exceeding capacity.
                    trip = self.addarc(nearestarcs[0], nearest, trip)
                elif (
                    len(nearestarcs) > 1
                ):  # Multiple closest arcs exisits, so need to break ties.
                    vehicleCost = 0
                    chosearc = self.choose_arc(
                        nearestarcs, self.tripload, vehicleCost, self.rule
                    )
                    trip = self.addarc(chosearc, nearest, trip)
            else:  # trip is full
                trip = self.addDepotArc(trip)
                self.routeTripsLists = deepcopy(trip)
                break

    def buildSolutionRouteDict(self):
        """
        Standard route solution encoding.
        """
        solution_dTemp = {}
        solution_dTemp["Cost"] = self.tripcost
        solution_dTemp["Load"] = self.tripload
        solution_dTemp["Deadhead"] = self.tripdeadhead
        solution_dTemp["Service"] = self.tripservicecosts
        solution_dTemp["Route"] = deepcopy(self.routeTripsLists)
        return solution_dTemp

    def buildMultipleRoutes(self, balanced=False):
        """
        Generate routes until all the required arcs are serviced.
        """
        # self._calc_elipse_input()
        solution = {}
        self.reqArcsUnassigned = deepcopy(self.reqArcs)
        nVehicles = -1
        self.totalcost = 0
        while self.reqArcsUnassigned:
            nVehicles += 1
            # print('\t Vehicle Route - %i'%nVehicles)
            solution[nVehicles] = {}
            if balanced:
                self.buildbalancedroute()
            else:
                self.buildroute()
            solution[nVehicles] = deepcopy(self.buildSolutionRouteDict())
            if solution[nVehicles]["Load"] == 0:
                # key print('ERROR WITH INPUT DATE')
                break
        solution["ProblemType"] = "CARP"
        solution["TotalCost"] = self.totalcost
        solution["nVehicles"] = nVehicles + 1
        self.tester(solution)
        return solution

    def EPS_five_rules(self, balanced=False):
        """
        Use one of five classical EPS rules to break ties.
        """
        # key print('solve 5 rules')
        solutions = []
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)

        for i, rule in enumerate(self.classic_rules):
            self.rule = rule
            s1 = self.buildMultipleRoutes(balanced)
            if not self.reduce_all_trips:
                solutions.append(deepcopy(s1))
            # self._allFullSolutions.append(deepcopy(s1))
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                solutions.append(deepcopy(s2))
                # self._allFullSolutions.append(deepcopy(s2))
                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"
            self._outputStats.append(outline)
        return solutions

    def EPS_random(
        self, rule="RandomArc", nSolutions=1000, outFileName="test_error.csv"
    ):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """
        balanced = False
        # key print('EPS - %s\n' %(rule))
        self.rule = rule
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)
        evaluatesolutions._write_output_to_file(outFileName, heading)
        for i in range(nSolutions):
            s1 = self.buildMultipleRoutes(balanced)
            t = clock()
            if not self.reduce_all_trips:
                self._allFullSolutions.append(deepcopy(s1))
                tF = clock() - t
                self._allSolutionsTime.append(tF)
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self._allFullSolutions.append(deepcopy(s2))
                tF = clock() - t
                self._allSolutionsTime.append(tF)

                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"

            self._outputStats.append(outline)
            # evaluatesolutions._write_output_to_file(outFileName, outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_random_tLimit(self, rule="RandomArc", timeLimit=1000, nMax=1000):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """

        self._allFullSolutions = []
        self._allSolutionsTime = []

        balanced = False
        # key print('EPS - %s\n' %(rule))
        self.rule = rule
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)
        # evaluatesolutions._write_output_to_file(outFileName, heading)
        i = 0
        t0 = clock()
        while (clock() - t0 < timeLimit) and (i < nMax):
            tLeft = timeLimit - (clock() - t0)
            i += 1
            t = clock()
            s1 = self.buildMultipleRoutes(balanced)
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )

            s2 = self.Reduce_Trips.reduce_trip(s1)[0]
            self._allFullSolutions.append(deepcopy(s2))
            tF = clock() - t
            self._allSolutionsTime.append(tF)

            incumbent_solutions_reduce_routes = evaluatesolutions.update_all_incumbents(
                s2, incumbent_solutions_reduce_routes
            )
            outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
            if (i % self.print_iter) == 0:
                # key print(i, nMax)
                # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i %.4f'%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles'],tLeft))
                pass
            outline += "\n"

            self._outputStats.append(outline)

            # evaluatesolutions._write_output_to_file(outFileName, outline)

    def EPS_random_break_even(self, rule, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """
        # key print('EPS Break Even - %s - Balanced %s\n' %(rule, balanced))
        self.resetIncumbent()
        self.rule = rule
        i = 0
        while True:
            i += 1
            s = self.buildMultipleRoutes(balanced)
            self.updateIncumbent(s)
            # key print('S %i \t Goal %i \t Cost %i \t #Vehicles %i '%(i+1, self.break_even_point, s['TotalCost'], s['nVehicles']))
            if self.break_even_iter_limit <= i:
                break
            if self.bestVehComp["TotalCost"] <= self.break_even_point:
                break
        return i

    def tester(self, solution):
        if self.testsolutions:
            test_solution(self.info, solution)

    def EPS_solver(self, rule_type, nSolutions=5, outFileName="test_error.csv"):
        balanced = False
        if rule_type == "EPS_five_rules":
            sol = self.EPS_five_rules(balanced)
        elif rule_type == "EPS_random_five_rules":
            sol = self.EPS_random("RandomRule", nSolutions, outFileName)
        elif rule_type == "EPS_random_arc":
            sol = self.EPS_random("RandomArc", nSolutions, outFileName)
        # self.disp.display_solution_info(self.bestVehComp)
        if self._got_to_scan:
            scan_mean = np.mean(self._got_to_scan)
        else:
            scan_mean = 0
        if self.elipse_forced:
            elipse_forced_mean = self.elipse_forced / nSolutions / self._ned
        else:
            elipse_forced_mean = 0
        return sol

    def EPS_break_even_solver(self, rule_type, balanced="Original"):
        if balanced == "Original":
            balanced = False
        else:
            balanced = True
        if rule_type == "EPS_random_five_rules":
            nSolutions = self.EPS_random_break_even("RandomRule", balanced)
        elif rule_type == "EPS_random_arc":
            nSolutions = self.EPS_random_break_even("RandomArc", balanced)
        self.disp.display_solution_info(self.bestVehComp)
        return (self.bestVehComp, nSolutions)


class EPS_IF(ExtendedPathScanning_Operators, TieBreakRules):
    """
    Build solution using Extended Path Scanning. Algorithm finds
    closest unserviced arc and use rules to break ties. Different rules
    yield different solutions, where the best one can be returned.
    """

    def __init__(self, info):
        TieBreakRules.__init__(self)
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcs = list(info.reqArcListActual)  # TODO: decide between
        # numpy or python
        self.depot = info.depotnewkey
        self.end_depot = self.depot
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.if_cost = info.if_cost_np
        self.if_arc = info.if_arc_np
        self.rule = "MaxDepo"
        self.classic_rules = ["MaxDepo", "MinDepo", "MaxYield", "MinYield", "Hybrid"]
        self.classic_if_rules = [
            "MaxDepo",
            "MinDepo",
            "MaxYield",
            "MinYield",
            "HybridIFdepto",
        ]
        self.IF_rules = ["MaxIF", "MinIF", "MaxYield", "MinYield", "HybridIFdepto"]
        self.all_rules = [
            "MaxDepo",
            "MinDepo",
            "MaxIF",
            "MinIF",
            "MaxYield",
            "MinYield",
            "Hybrid",
            "HybridIFdepto",
        ]
        self.testsolutions = False
        self.info = info
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehN = {}
        self.c_modules = True
        self.disp = display_solution_stats(info)

        self.Reduce_Trips = Reduce_Trips(info)
        self.reduce_all_trips = True
        self.reduce_all_trips_v2 = False
        self.reduce_all_trips_v3 = False
        self.reduce_best_trips = False
        self.improve_IFs = False

        self.break_even_point = 1e300000
        self.break_even_iter_limit = 100

        self.write_output = False
        self.file_write = ""
        self.file_name = ""

        self.elipse_rule = False
        self.elipse_alpha = 1.5
        self.elipse_frac = 0.95
        self.print_iter = 1
        self._got_to_scan = []
        self.inc_frac = 1.5

        self.nRoutesLB = 0
        self._allSolutions = []
        self._saveSolutions = False
        self._allFullSolutions = []
        self._allSolutionsTime = []

    def _calc_elipse_input(self):
        ned = 0
        td = 0
        tc = 0
        arc_added = self.info.reqArcList[:]
        for arc in self.reqArcs:
            if arc_added[arc] != None:
                ned += 1
                td += self.demand[arc]
                tc += self.serveCost[arc]
                if self.invArcList[arc] != None:
                    arc_added[self.invArcList[arc]] = None
        self._ned = ned
        self._td = td
        self._tc = tc
        self._ned_left = ned

    def addarc(self, arc, nearest, trip):
        """
        Add arc to trip and update all cost and load info.
        """
        self.totalcost += self.serveCost[arc] + nearest
        self.routecost += self.serveCost[arc] + nearest
        self.routedeadhead += nearest
        self.routeload += self.demand[arc]
        self.routeservicecosts += self.serveCost[arc]
        self.tripcost += self.serveCost[arc] + nearest
        self.tripdeadhead += nearest
        self.tripload += self.demand[arc]
        self.tripservicecosts += self.serveCost[arc]

        arc1 = self.reqArcsUnassigned.index(arc)
        if self.invArcList[arc]:
            arc2 = self.reqArcsUnassigned.index(self.invArcList[arc])
            del self.reqArcsUnassigned[max(arc1, arc2)]
            del self.reqArcsUnassigned[min(arc1, arc2)]
        else:
            del self.reqArcsUnassigned[arc1]

        # self._ned_left -= 1
        trip.append(arc)
        return trip

    def addIFarc(self, arc, nearest, trip):
        """
        Add IF visit to trip and update cost data.
        """
        dumparc = self.if_arc[trip[-1]][arc]
        dumptripcost = self.d[trip[-1]][dumparc] + self.dumpCost
        self.routecost += dumptripcost
        self.totalcost += dumptripcost
        self.routedeadhead += dumptripcost
        self.tripcost += dumptripcost
        self.tripdeadhead += dumptripcost
        trip.append(dumparc)
        return trip

    def addIFDepotArc(self, trip):
        """
        Close route by adding a IF then depot visit.
        """
        dumpvisit_cost = self.if_cost[trip[-1]][self.end_depot]
        self.routecost += dumpvisit_cost
        self.totalcost += dumpvisit_cost
        self.routedeadhead += dumpvisit_cost
        self.tripcost += dumpvisit_cost
        self.tripdeadhead += dumpvisit_cost
        trip.append(self.if_arc[trip[-1]][self.end_depot])
        trip.append(self.end_depot)
        return trip

    def initialise_trip(self):
        self.ntrips = 1
        self.routecost = 0
        self.routedeadhead = 0
        self.routeload = 0
        self.routeservicecosts = 0
        self.tripcost = 0
        self.tripdeadhead = 0
        self.tripload = 0
        self.tripservicecosts = 0

        self.routeTripsLists = []
        self.routeLoadsLists = []
        self.routeCostsLists = []
        self.routeDeadheadLists = []
        self.routeServiceCostLists = []

    def reset_trip(self, trip):
        self.routeTripsLists.append(deepcopy(trip))  # Update and reset trip info
        self.routeLoadsLists.append(self.tripload)
        self.tripload = 0
        self.routeCostsLists.append(self.tripcost)
        self.tripcost = 0
        self.routeDeadheadLists.append(self.tripdeadhead)
        self.tripdeadhead = 0
        self.routeServiceCostLists.append(self.tripservicecosts)
        self.tripservicecosts = 0

    def _check_elipse_capacity_rule(self, tripload):
        if self.elipse_rule:
            if (self.capacity - tripload) <= (self.elipse_alpha * self._td / self._ned):
                return True
            else:
                return False
        else:
            return False

    def _check_elipse_cost_rule(self, routeCost):
        if self.elipse_rule:
            if (routeCost) >= (self.elipse_frac * self.maxTrip):
                return True
            else:
                return False
        else:
            return False

    def buildIFroute(self):
        """
        Build IF route by finding the closest unserviced arc. Arc is added
        to a trip if it doesn't exceed vehicle capacity and maxtrip lenght.
        IF a trip is full, an IF visit is added. IF a route is full, an IF and
        depot visit is added.
        """
        # self._calc_elipse_input()
        self.initialise_trip()
        trip = [self.depot]
        while True:
            elipse_cost_flag = self._check_elipse_cost_rule(self.routecost)
            elipse_capacity_flag = self._check_elipse_capacity_rule(self.tripload)
            previousarc = trip[-1]
            if elipse_cost_flag:
                if self.c_modules:
                    (nearestarcs, nearest, k) = self.c_findnearestarcs_elipse(
                        previousarc
                    )
                else:
                    (nearestarcs, nearest, k) = self.findnearestarcs_elipse(previousarc)
                # self._got_to_scan.append(k/self._ned_left)
            #             elif elipse_capacity_flag:
            if elipse_capacity_flag:
                if self.c_modules:
                    (nearestarcs, nearest, k) = self.c_findnearestarcs_cap_elipse(
                        previousarc
                    )
                else:
                    (nearestarcs, nearest, k) = self.findnearestarcs_cap_elipse(
                        previousarc
                    )
                # self._got_to_scan.append(k/self._ned_left)
            else:
                if self.c_modules:
                    (nearestarcs, nearest) = self.c_findnearestarcs(previousarc)
                else:
                    (nearestarcs, nearest) = self.findnearestarcs(previousarc)
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                chosearc = self.choose_arc(
                    nearestarcs, self.tripload, self.routecost, self.rule
                )
                trip = self.addarc(chosearc, nearest, trip)
            else:  # trip is full
                #                 if elipse_cost_flag:
                #                     if self.c_modules:
                #                         (nearestarcs, nearest, k) = self.c_findnearestIFarcs_elipse(previousarc)
                #                     else:
                #                         (nearestarcs, nearest, k) = self.findnearestIFarcs_elipse(previousarc)
                #                     #self._got_to_scan.append(k/self._ned_left)
                #                 else:
                if self.c_modules:
                    (nearestarcs, nearest) = self.c_findnearestIFarcs(previousarc)
                else:
                    (nearestarcs, nearest) = self.findnearestIFarcs(previousarc)
                if (
                    nearestarcs
                ):  # arc can be added after IF visit without exceeding max route length.
                    self.ntrips += 1
                    if len(nearestarcs) == 1:
                        chosearc = nearestarcs[0]
                    elif (
                        len(nearestarcs) > 1
                    ):  # Multiple closest arcs exists, so need to break ties.
                        chosearc = self.choose_arc(
                            nearestarcs, self.tripload, self.routecost, self.rule
                        )
                    trip = self.addIFarc(
                        chosearc, nearest, trip
                    )  # Add IF visit to end of trip
                    self.reset_trip(trip)
                    trip = [trip[-1]]  # begin new trip with IF visit
                    nearest = self.d[trip[-1]][chosearc]
                    trip = self.addarc(chosearc, nearest, trip)
                else:  # Route is full.
                    trip = self.addIFDepotArc(trip)
                    self.reset_trip(trip)
                    break

    def buildbalancedIFroute(self):
        """
        Build IF route by finding the closest unserviced arc. Closest arc is added
        to a trip if it doesn't exceed vehicle capacity and maxtrip lenght. If closest
        arc exceeds these limits the trip is considered full. IF a trip is full, an
        IF visit is added. IF a route is full, an IF and depot visit is added.
        """
        self.initialise_trip()
        trip = [self.depot]

        while True:
            previousarc = trip[-1]
            (nearestarcs, nearest) = self.findnearestarcsbalanced(previousarc)
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                chosearc = self.choose_arc(
                    nearestarcs, self.tripload, self.routecost, self.rule
                )
                trip = self.addarc(chosearc, nearest, trip)
            elif len(trip) == 1:  # trip is full
                if self.c_modules:
                    (nearestarcs, nearest) = self.c_findnearestarcs(previousarc)
                else:
                    (nearestarcs, nearest) = self.findnearestarcs(previousarc)
                if (
                    len(nearestarcs) == 1
                ):  # Arc can be added without exceeding capacity.
                    trip = self.addarc(nearestarcs[0], nearest, trip)
                elif (
                    len(nearestarcs) > 1
                ):  # Multiple closest arcs exisits, so need to break ties.
                    chosearc = self.choose_arc(
                        nearestarcs, self.tripload, self.routecost, self.rule
                    )
                    trip = self.addarc(chosearc, nearest, trip)
            else:
                if self.c_modules:
                    (nearestarcs, nearest) = self.c_findnearestIFarcs(previousarc)
                else:
                    (nearestarcs, nearest) = self.findnearestIFarcs(previousarc)
                if (
                    nearestarcs
                ):  # arc can be added after IF visit without exceeding max route length.
                    self.ntrips += 1
                    if len(nearestarcs) == 1:
                        chosearc = nearestarcs[0]
                    elif (
                        len(nearestarcs) > 1
                    ):  # Multipl closest arcs exists, so need to break ties.
                        chosearc = self.choose_arc(
                            nearestarcs, self.tripload, self.routecost, self.rule
                        )
                    trip = self.addIFarc(
                        chosearc, nearest, trip
                    )  # Add IF visit to end of trip
                    self.reset_trip(trip)
                    trip = [trip[-1]]  # begin new trip with IF visit
                    nearest = self.d[trip[-1]][chosearc]
                    trip = self.addarc(chosearc, nearest, trip)
                else:  # Route is full.
                    trip = self.addIFDepotArc(trip)
                    self.reset_trip(trip)
                    break

    def buildSolutionIFRouteDict(self):
        """
        Standard route solution encoding.
        """
        solution_dTemp = {}
        solution_dTemp["Cost"] = self.routecost
        solution_dTemp["TripCosts"] = deepcopy(self.routeCostsLists)
        solution_dTemp["Load"] = self.routeload
        solution_dTemp["TripLoads"] = deepcopy(self.routeLoadsLists)
        solution_dTemp["Deadhead"] = self.routedeadhead
        solution_dTemp["TripDeadheads"] = deepcopy(self.routeDeadheadLists)
        solution_dTemp["Service"] = self.routeservicecosts
        solution_dTemp["TripServices"] = deepcopy(self.routeServiceCostLists)
        solution_dTemp["Trips"] = deepcopy(self.routeTripsLists)
        solution_dTemp["nTrips"] = self.ntrips
        return solution_dTemp

    def buildMultipleIFRoutes(self, outFileName=None, balanced=False):
        """
        Generate routes until all the required arcs are serviced.
        """
        solution = {}
        self.reqArcsUnassigned = deepcopy(self.reqArcs)
        nVehicles = -1
        self.totalcost = 0
        while len(self.reqArcsUnassigned) != 0:
            nVehicles += 1
            # print('\t Vehicle Route - %i'%nVehicles)
            solution[nVehicles] = {}
            if balanced:
                self.buildbalancedIFroute()
            else:
                self.buildIFroute()
            solution[nVehicles] = deepcopy(self.buildSolutionIFRouteDict())
            if solution[nVehicles]["Load"] == 0:
                # key print('ERROR WITH INPUT DATE')
                break
        solution["ProblemType"] = "CLARPIF"
        solution["TotalCost"] = self.totalcost
        solution["nVehicles"] = nVehicles + 1
        self.tester(solution)
        return solution

    def EPS_all_rules(self, outFileName, balanced=False):
        """
        Use one of five classical EPS rules to break ties.
        """
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        self.giantroute = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"

        if outFileName:
            # key print(outFileName)
            if not os.path.isfile(outFileName):
                evaluatesolutions._write_output_to_file(outFileName, heading)
        self._outputStats.append(heading)
        for i, rule in enumerate(self.all_rules):
            self.rule = rule
            s1 = self.buildMultipleIFRoutes(balanced)
            self.giantroute.append(deepcopy(s1))
            self._allFullSolutions.append(deepcopy(s1))
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%s,%i,%i" % (rule, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %s RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(rule, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self._allFullSolutions.append(deepcopy(s2))
                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %s RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(rule,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"
            self._outputStats.append(outline)
            if outFileName:
                evaluatesolutions._write_output_to_file(outFileName, outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_five_rules(self, outFileName=None, balanced=False):
        """
        Use one of five classical EPS rules to break ties.
        """
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)
        # evaluatesolutions._write_output_to_file(outFileName, heading)
        for i, rule in enumerate(self.classic_rules):
            self.rule = rule
            s1 = self.buildMultipleIFRoutes(balanced)
            self._allFullSolutions.append(deepcopy(s1))
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%s,%i,%i" % (rule, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %s RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(rule, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self._allFullSolutions.append(deepcopy(s2))
                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %s RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(rule,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"
            self._outputStats.append(outline)
            # evaluatesolutions._write_output_to_file(outFileName, outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_one_rules(self, ruleType):
        """
        Use one of five classical EPS rules to break ties.
        """
        balanced = False
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)
        # evaluatesolutions._write_output_to_file(outFileName, heading)
        self.rule = ruleType
        s1 = self.buildMultipleIFRoutes(balanced)
        self._allFullSolutions.append(deepcopy(s1))
        # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
        outline = "%s,%i,%i" % (ruleType, s1["TotalCost"], s1["nVehicles"])
        incumbent_solutions = evaluatesolutions.update_all_incumbents(
            s1, incumbent_solutions
        )
        if (1 % self.print_iter) == 0:
            # key print('S %s RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(ruleType, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
            pass
        i = 0
        if self.reduce_all_trips:
            s2 = self.Reduce_Trips.reduce_trip(s1)[0]
            self._allFullSolutions.append(deepcopy(s2))
            incumbent_solutions_reduce_routes = evaluatesolutions.update_all_incumbents(
                s2, incumbent_solutions_reduce_routes
            )
            outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
            if (i % self.print_iter) == 0:
                # key print('S %s RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(ruleType,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                pass
        outline += "\n"
        self._outputStats.append(outline)
        # evaluatesolutions._write_output_to_file(outFileName, outline)
        return (s1, incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_five_rules_IFs(self, outFileName, balanced=False):
        """
        Use one of five five EPS rules to break ties.
        """
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)
        # evaluatesolutions._write_output_to_file(outFileName, heading)

        for i, rule in enumerate(self.IF_rules):
            self.rule = rule
            s1 = self.buildMultipleIFRoutes(balanced)
            self._allFullSolutions.append(deepcopy(s1))
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self._allFullSolutions.append(deepcopy(s2))
                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"
            self._outputStats.append(outline)
            # evaluatesolutions._write_output_to_file(outFileName, outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_IF_all_rules_IFs(self, balanced=False):
        """
        Use one of eight rules, old and new, to break ties.
        """
        # key print('EPS with IFs - All 8 Rules - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_all_rules"
        solutionsOutput["Balanced"] = balanced
        for rule in self.all_rules:
            # key print('Solution %s'%rule)
            self.rule = rule
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[rule] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_rules(self, rules, balanced=False):
        """
        Use one of eight rules, old and new, to break ties.
        """
        if self.improve_IFs:
            part.populate_c_local_search(self.info, True)
            improve_IFs = part.UlusoysIFs_1vehicle(self.info)

        # key print('EPS with IFs - %i Rules - Balanced %s\n' %(len(rules), balanced))
        self.resetIncumbent()
        solutions = []
        for rule in rules:
            self.rule = rule
            t = clock()
            s = self.buildMultipleIFRoutes(balanced)
            if self.improve_IFs:
                s = improve_IFs.improve_solution(s)
            if self.reduce_all_trips:
                s = self.Reduce_Trips.reduce_trip(s)[0]
            # print('S %s \t Cost %i \t nVehicles %i '%(rule, s['TotalCost'], s['nVehicles']))
            self.updateIncumbent(s)
            solutions.append((s["TotalCost"], s["nVehicles"], clock() - t))
        if self.reduce_best_trips:
            self.bestVehComp = self.Reduce_Trips.reduce_trip(self.bestVehComp)[0]

        if self.improve_IFs:
            part.free_c_local_search(True)

        return solutions

    def EPS_IF_random_five_rules(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """
        self.rule = "RandomRule"

        # key print('EPS with IFs - Random 5 Rule - Balanced %s\n' %balanced)
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        self._outputStats.append(heading)
        for i in range(nSolutions):
            s1 = self.buildMultipleIFRoutes(balanced)
            self._allFullSolutions.append(deepcopy(s1))
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self._allFullSolutions.append(deepcopy(s2))
                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"
            self._outputStats.append(outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_IF_random_five_IF_rules(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a new IF rule to break ties.
        """
        # key print('EPS with IFs - Random 5 Rule IF rules - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_five_IF_rules"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomRuleIFs"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random_all_rules(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a new or classical rule to break ties.
        """
        # key print('EPS with IFs - Random 8 Rule - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_all_rules"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomRuleAll"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random_arc(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        an arc to break ties.
        """
        # key print('EPS with IFs - Random Arc Rule - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_arc"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomArc"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random(self, rule, nSolutions=8, outFileName=None, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """

        # print('EPS - %s - Balanced %s\n' %(rule, balanced))
        self.rule = rule
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        self.giantroute = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        # if not os.path.isfile(outFileName):
        self._outputStats.append(heading)
        # evaluatesolutions._write_output_to_file(outFileName, heading)
        for i in range(nSolutions):
            self.t1 = clock()
            s1 = self.buildMultipleIFRoutes(balanced)
            self.t2 = clock() - self.t1
            self.giantroute.append(deepcopy(s1))
            self._allFullSolutions.append(deepcopy(s1))
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if ((i + 1) % self.print_iter) == 0:
                # key print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
                pass
            if self.reduce_all_trips:
                self.t3 = clock()
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self.t4 = clock() - self.t3
                self._allFullSolutions.append(deepcopy(s2))
                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if ((i + 1) % self.print_iter) == 0:
                    # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    pass
            outline += "\n"
            self._outputStats.append(outline)
            # evaluatesolutions._write_output_to_file(outFileName, outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_IF_random_tLimit(self, rule="RandomArc", timeLimit=1000, nMax=1000):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """
        balanced = False
        # key print('EPS - %s - Balanced %s\n' %(rule, balanced))
        self.rule = rule
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        # rr -> reduce_routes
        s1 = {}
        s2 = {}
        self._outputStats = []
        self.giantroute = []
        # self._outputStats.append(self.info.name + '\n')
        if self.reduce_all_trips:
            heading = "T,Z,K,RR_Z,RR_K\n"
        else:
            heading = "T,Z,K\n"
        # if not os.path.isfile(outFileName):
        self._outputStats.append(heading)
        # evaluatesolutions._write_output_to_file(outFileName, heading)
        i = 0
        t0 = clock()
        while clock() - t0 < timeLimit and i < nMax:
            tLeft = timeLimit - (clock() - t0)
            i += 1
            t = clock()
            s1 = self.buildMultipleIFRoutes(balanced)
            if not self.reduce_all_trips:
                self._allFullSolutions.append(deepcopy(s1))
                tF = clock() - t
                self._allSolutionsTime.append(tF)
            # self._outputStats.append([s1['TotalCost'],s1['nVehicles']])
            outline = "%i,%i,%i" % (i, s1["TotalCost"], s1["nVehicles"])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(
                s1, incumbent_solutions
            )
            if (i % self.print_iter) == 0:
                # key print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i %.4f'%(i+1, s1['TotalCost'], s1['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles'],tLeft))
                pass
            if self.reduce_all_trips:
                s2 = self.Reduce_Trips.reduce_trip(s1)[0]
                self._allFullSolutions.append(deepcopy(s2))
                tF = clock() - t
                self._allSolutionsTime.append(tF)

                incumbent_solutions_reduce_routes = (
                    evaluatesolutions.update_all_incumbents(
                        s2, incumbent_solutions_reduce_routes
                    )
                )
                outline += ",%i,%i" % (s2["TotalCost"], s2["nVehicles"])
                if (i % self.print_iter) == 0:
                    # key print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i %.4f'%(i+1,  s2['TotalCost'], s2['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles'],tLeft))
                    pass
            outline += "\n"

            self._outputStats.append(outline)
            # evaluatesolutions._write_output_to_file(outFileName, outline)
        return (incumbent_solutions, incumbent_solutions_reduce_routes)

    def EPS_IF_random_break_even(self, rule, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        an arc to break ties.
        """
        # key print('EPS with IFs Break Even - %s - Balanced %s\n' %(rule, balanced))
        self.resetIncumbent()
        self.rule = rule
        i = 0
        while True:
            i += 1
            s = self.buildMultipleIFRoutes(balanced)
            self.updateIncumbent(s)
            # key print('S %i \t Goal %i \t Cost %i \t #Vehicles %i '%(i+1, self.break_even_point, s['TotalCost'], s['nVehicles']))
            if self.break_even_iter_limit <= i:
                break
            if self.bestVehComp["TotalCost"] <= self.break_even_point:
                break
        return i

    def EPS_IF_solver(
        self, rule_type, nSolutions=5, outFileName=None, balanced="Original"
    ):
        if balanced == "Original":
            balanced = False
        else:
            balanced = True
        if rule_type == "EPS_five_rules":  # Do not use
            sol = self.EPS_five_rules(outFileName, balanced)
        elif rule_type == "EPS_five_IF_rules":  # Do not use
            sol = self.EPS_five_rules_IFs(outFileName, balanced)
        if rule_type == "EPS_all_rules":  # Do not use
            sol = self.EPS_all_rules(outFileName, balanced)
        elif rule_type == "EPS_random_five_rules":  # Use
            sol = self.EPS_IF_random("RandomRule", nSolutions, outFileName, balanced)
        elif rule_type == "EPS_random_five_IF_rules":  # Do not use
            sol = self.EPS_IF_random("RandomRuleIFs", nSolutions, outFileName, balanced)
        elif rule_type == "EPS_random_arc":  # Use
            sol = self.EPS_IF_random("RandomArc", nSolutions, balanced)
        elif rule_type == "EPS_IF_random_all_rules":  # Do no use
            sol = self.EPS_IF_random("RandomRuleAll", nSolutions, balanced)
        return sol

    #         elif rule_type == 'EPS_IF_five_rules': # Use
    #             sol = self.EPS_IF_rules(self.classic_rules, balanced)
    #         elif rule_type == 'EPS_IF_all_rules': # Do not use
    #             sol = self.EPS_IF_rules(self.all_rules, balanced)

    def EPS_IF_break_even_solver(self, rule_type, balanced="Original"):
        if balanced == "Original":
            balanced = False
        else:
            balanced = True
        if rule_type == "EPS_IF_random_five_rules":
            nSolutions = self.EPS_IF_random_break_even("RandomRule", balanced)
        elif rule_type == "EPS_IF_random_five_IF_rules":
            nSolutions = self.EPS_IF_random_break_even("RandomRuleIFs", balanced)
        elif rule_type == "EPS_IF_random_all_rules":
            nSolutions = self.EPS_IF_random_break_even("RandomRuleAll", balanced)
        elif rule_type == "EPS_random_arc":
            nSolutions = self.EPS_IF_random_break_even("RandomArc", balanced)
        self.disp.display_solution_info(self.bestVehComp)
        return (self.bestVehComp, nSolutions)

    def tester(self, solution):
        if self.testsolutions:
            test_solution(self.info, solution)


class EPS_GiantRoute(ExtendedPathScanning_Operators, TieBreakRules):
    def __init__(self, info):
        TieBreakRules.__init__(self)
        self.capacity = info.capacity
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.end_depot = self.depot
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.c_modules = True

    def addarc(self, arc, nearest, trip):
        """
        Add arc to trip and update all cost and load info.
        """
        arc1 = self.reqArcsUnassigned.index(arc)
        if self.invArcList[arc]:
            arc2 = self.reqArcsUnassigned.index(self.invArcList[arc])
            del self.reqArcsUnassigned[max(arc1, arc2)]
            del self.reqArcsUnassigned[min(arc1, arc2)]
        else:
            del self.reqArcsUnassigned[arc1]
        trip.append(arc)
        return trip

    def buildroute(self, rule="MaxDepo"):
        """
        Build IF route by finding the closest unserviced arc. Closest arc is added
        to a trip if it doesn't exceed vehicle capacity and maxtrip lenght. If closest
        arc exceeds these limits the trip is considered full. IF a trip is full, an
        IF visit is added. IF a route is full, an IF and depot visit is added.
        """

        trip = [self.depot]
        while self.reqArcsUnassigned:
            previousarc = trip[-1]
            if self.c_modules:
                (nearestarcs, nearest) = self.c_findnearestarcsbalanced_sub1(
                    previousarc
                )
            else:
                (nearestarcs, nearest) = self.findnearestarcsbalanced_sub1(previousarc)
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                chosearc = self.choose_arc(nearestarcs, None, None, rule)
                trip = self.addarc(chosearc, nearest, trip)
        return trip[1:]

    def buildgiantroute(self, rule):
        """
        Generate routes until all the required arcs are serviced.
        """
        self.reqArcsUnassigned = deepcopy(self.reqArcs)
        return self.buildroute(rule)


class EPS_MultipleGiantRoute(ExtendedPathScanning_Operators, TieBreakRules):
    """
    Build solution using Extended Path Scanning. Algorithm finds
    closest unserviced arc and use rules to break ties. Different rules
    yield different solutions, where the best one can be returned.
    """

    def __init__(self, info):
        TieBreakRules.__init__(self)
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.end_depot = self.depot
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.if_cost = info.if_cost_np
        self.if_arc = info.if_arc_np
        self.rule = "MaxDepo"
        self.classic_rules = ["MaxDepo", "MinDepo", "MaxYield", "MinYield", "Hybrid"]
        self.IF_rules = ["MaxIF", "MinIF", "MaxYield", "MinYield", "HybridIFdepto"]
        self.all_rules = [
            "MaxDepo",
            "MinDepo",
            "MaxIF",
            "MinIF",
            "MaxYield",
            "MinYield",
            "Hybrid",
            "HybridIFdepto",
        ]
        self.testsolutions = True
        self.info = info
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehN = {}
        self.c_modules = True
        self.stats = ()
        self.calcstats = True
        self.calstatslimit = 0.75 * self.maxTrip
        self.partition = py_alg_ulusoy_partition.UlusoysIFs_1vehicle(self.info)
        self.disp = display_solution_stats(info)

    def if_cost_function(self, nDumps):
        route_average = self.stats[0]
        temp_cost = int(nDumps * route_average)
        return temp_cost

    def estimate_if_cost(self, trip):
        self.stats = py_solution_stats.route_IF_cost_stats(
            trip[1:], self.d, self.if_cost
        )
        nDumps = max(0, int(ceil(float(self.tripload) / float(self.capacity)) - 1))
        return self.if_cost_function(nDumps)

    def addarc(self, arc, nearest, trip):
        """
        Add arc to trip and update all cost and load info.
        """
        self.totalcost += self.serveCost[arc] + nearest
        self.routecost += self.serveCost[arc] + nearest
        self.routedeadhead += nearest
        self.routeload += self.demand[arc]
        self.routeservicecosts += self.serveCost[arc]
        self.tripcost += self.serveCost[arc] + nearest
        self.tripdeadhead += nearest
        self.tripload += self.demand[arc]
        self.tripservicecosts += self.serveCost[arc]

        arc1 = self.reqArcsUnassigned.index(arc)
        if self.invArcList[arc]:
            arc2 = self.reqArcsUnassigned.index(self.invArcList[arc])
            del self.reqArcsUnassigned[max(arc1, arc2)]
            del self.reqArcsUnassigned[min(arc1, arc2)]
        else:
            del self.reqArcsUnassigned[arc1]

        trip.append(arc)
        return trip

    def addIFDepotArc(self, trip):
        """
        Close route by adding a IF then depot visit.
        """
        dumpvisit_cost = self.if_cost[trip[-1]][self.end_depot]
        self.routecost += dumpvisit_cost
        self.totalcost += dumpvisit_cost
        self.routedeadhead += dumpvisit_cost
        self.tripcost += dumpvisit_cost
        self.tripdeadhead += dumpvisit_cost
        trip.append(self.if_arc[trip[-1]][self.end_depot])
        trip.append(self.end_depot)
        return trip

    def initialise_trip(self):
        self.ntrips = 1
        self.routecost = 0
        self.routedeadhead = 0
        self.routeload = 0
        self.routeservicecosts = 0
        self.tripcost = 0
        self.tripdeadhead = 0
        self.tripload = 0
        self.tripservicecosts = 0

        self.routeTripsLists = []
        self.routeLoadsLists = []
        self.routeCostsLists = []
        self.routeDeadheadLists = []
        self.routeServiceCostLists = []

    def reset_trip(self, trip):
        self.routeTripsLists.append(deepcopy(trip))  # Update and reset trip info
        self.routeLoadsLists.append(self.tripload)
        self.tripload = 0
        self.routeCostsLists.append(self.tripcost)
        self.tripcost = 0
        self.routeDeadheadLists.append(self.tripdeadhead)
        self.tripdeadhead = 0
        self.routeServiceCostLists.append(self.tripservicecosts)
        self.tripservicecosts = 0

    def buildIFroute(self):
        """
        Build IF route by finding the closest unserviced arc. Arc is added
        to a trip if it doesn't exceed vehicle capacity and maxtrip lenght.
        IF a trip is full, an IF visit is added. IF a route is full, an IF and
        depot visit is added.
        """
        self.initialise_trip()
        trip = [self.depot]
        while True:
            previousarc = trip[-1]
            if len(trip) > 2:
                average_if_cost = self.estimate_if_cost(trip)
            else:
                average_if_cost = 0
            if self.c_modules:
                (nearestarcs, nearest) = self.c_findnearestarcs_noload(
                    previousarc, average_if_cost
                )
            else:
                (nearestarcs, nearest) = self.findnearestarcs_noload(
                    previousarc, average_if_cost
                )
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                chosearc = self.choose_arc(
                    nearestarcs, self.tripload, self.routecost, self.rule
                )
                trip = self.addarc(chosearc, nearest, trip)
            else:
                trip = self.addIFDepotArc(trip)
                self.reset_trip(trip)
                break

    def buildbalancedIFroute(self):
        """
        Build IF route by finding the closest unserviced arc. Closest arc is added
        to a trip if it doesn't exceed vehicle capacity and maxtrip lenght. If closest
        arc exceeds these limits the trip is considered full. IF a trip is full, an
        IF visit is added. IF a route is full, an IF and depot visit is added.
        """
        self.initialise_trip()
        trip = [self.depot]

        while True:
            previousarc = trip[-1]
            if len(trip) > 2:
                average_if_cost = self.estimate_if_cost(trip)
            else:
                average_if_cost = 0
            (nearestarcs, nearest) = self.findnearestarcsbalanced_noload(
                previousarc, average_if_cost
            )
            if len(nearestarcs) == 1:  # Arc can be added without exceeding capacity.
                trip = self.addarc(nearestarcs[0], nearest, trip)
            elif (
                len(nearestarcs) > 1
            ):  # Multiple closest arcs exisits, so need to break ties.
                chosearc = self.choose_arc(
                    nearestarcs, self.tripload, self.routecost, self.rule
                )
                trip = self.addarc(chosearc, nearest, trip)
            else:  # trip is full
                trip = self.addIFDepotArc(trip)
                self.reset_trip(trip)
                break

    def buildSolutionIFRouteDict(self):
        """
        Standard route solution encoding.
        """
        solution_dTemp = {}
        solution_dTemp["Cost"] = self.routecost
        solution_dTemp["TripCosts"] = deepcopy(self.routeCostsLists)
        solution_dTemp["Load"] = self.routeload
        solution_dTemp["TripLoads"] = deepcopy(self.routeLoadsLists)
        solution_dTemp["Deadhead"] = self.routedeadhead
        solution_dTemp["TripDeadheads"] = deepcopy(self.routeDeadheadLists)
        solution_dTemp["Service"] = self.routeservicecosts
        solution_dTemp["TripServices"] = deepcopy(self.routeServiceCostLists)
        solution_dTemp["Trips"] = deepcopy(self.routeTripsLists)
        solution_dTemp["nTrips"] = self.ntrips
        return solution_dTemp

    def partition_routes(self, solution):
        nVehicles = solution["nVehicles"]
        complete_route = []
        for i in xrange(nVehicles):
            complete_route.append(
                self.partition.gen_solution_list(solution[i]["Trips"][0][1:-2])[0]
            )
        return complete_route

    def buildMultipleIFRoutes(self, balanced=False):
        """
        Generate routes until all the required arcs are serviced.
        """
        solution = {}
        self.reqArcsUnassigned = deepcopy(self.reqArcs)
        nVehicles = -1
        self.totalcost = 0
        while self.reqArcsUnassigned:
            nVehicles += 1
            # key print('\t Vehicle Route - %i'%nVehicles)
            solution[nVehicles] = {}
            if balanced:
                self.buildbalancedIFroute()
            else:
                self.buildIFroute()
            solution[nVehicles] = deepcopy(self.buildSolutionIFRouteDict())
            if solution[nVehicles]["Load"] == 0:
                # key print('ERROR WITH INPUT DATE')
                break

        solution["ProblemType"] = "CLARPIF"
        solution["TotalCost"] = self.totalcost
        solution["nVehicles"] = nVehicles + 1
        solution_with_ifs = self.partition_routes(solution)
        solution = build_solution.build_CLARPIF_dict(
            solution_with_ifs,
            self.if_arc,
            self.depot,
            self.d,
            self.serveCost,
            self.dumpCost,
            self.demand,
        )
        self.disp.display_solution_info(solution)
        self.tester(solution)
        # key print('')
        return solution

    def resetIncumbent(self):
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehN = {}

    def updateIncumbent(self, solution):
        if solution["TotalCost"] < self.bestSol:
            self.bestSol = solution["TotalCost"]
            self.bestSolN = solution["nVehicles"]
            self.bestSolComp = deepcopy(solution)
        if solution["nVehicles"] < self.bestVehN:
            self.bestVeh = solution["TotalCost"]
            self.bestVehN = solution["nVehicles"]
            self.bestVehN = deepcopy(solution)
        elif (solution["nVehicles"] == self.bestVehN) & (
            solution["TotalCost"] < self.bestVeh
        ):
            self.bestVeh = solution["TotalCost"]
            self.bestVehN = solution["nVehicles"]
            self.bestVehN = deepcopy(solution)

    def EPS_IF_five_rules(self, balanced=False):
        """
        Use one of five classical EPS rules to break ties.
        """
        # key print('EPS with IFs - All 5 Rules - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_five_rules"
        solutionsOutput["Balanced"] = balanced
        for rule in self.classic_rules:
            # key print('Solution %s'%rule)
            self.rule = rule
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[rule] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_five_rules_IFs(self, balanced=False):
        """
        Use one of five new IF based rules to break ties.
        """
        # key print('EPS with IFs - All 5 IF Rules - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_five_IF_rules_IF"
        solutionsOutput["Balanced"] = balanced
        for rule in self.IF_rules:
            # key print('Solution %s'%rule)
            self.rule = rule
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[rule] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_all_rules_IFs(self, balanced=False):
        """
        Use one of eight rules, old and new, to break ties.
        """
        # key print('EPS with IFs - All 8 Rules - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_five_rules_IFs"
        solutionsOutput["Balanced"] = balanced
        for rule in self.all_rules:
            # key print('Solution %s'%rule)
            self.rule = rule
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[rule] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random_five_rules(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        """
        # key print('EPS with IFs - Random 5 Rule - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_five_rules"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomRule"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random_five_IF_rules(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a new IF rule to break ties.
        """
        # key print('EPS with IFs - Random 5 Rule IF rules - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_five_IF_rules"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomRuleIFs"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random_all_rules(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        a new or classical rule to break ties.
        """
        # key print('EPS with IFs - Random 8 Rule - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_all_rules"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomRuleAll"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def EPS_IF_random_arc(self, nSolutions=8, balanced=False):
        """
        Generate a specified number of solutions by randomly choosing
        an arc to break ties.
        """
        # key print('EPS with IFs - Random Arc Rule - Balanced %s\n' %balanced)
        self.resetIncumbent()
        solutionsOutput = {}
        solutionsOutput["Type"] = "EPS_IF_random_arc"
        solutionsOutput["Balanced"] = balanced
        self.rule = "RandomArc"
        for i in range(nSolutions):
            # key print('Solution %i'%(i+1))
            s = self.buildMultipleIFRoutes(balanced)
            solutionsOutput[i] = deepcopy(s)
            self.updateIncumbent(s)
        return solutionsOutput

    def tester(self, solution):
        if self.testsolutions:
            test_solution(self.info, solution)


import converter.py_return_problem_data as py_return_problem_data


def test_merge(problem_set="Centurion"):
    problems = [
        "mval_IF_3L",
        "Lpr_IF",
        "Lpr_IF_075L",
    ]  # [ 'gdb_IF', 'bccm_IF', 'gdb_IF_3L', 'bccm_IF_3L','mval_IF_15L', 'mval_IF_3L', 'Lpr_IF', 'Lpr_IF_075L']
    for problem_set in problems:
        problem_list = py_return_problem_data.return_problem_data_list(problem_set)
        problem_list.sort()
        extension = [
            "_Balanced_v2",
            "_Normal_v2",
        ]  # ['_Normal_NR','_Balanced_NR', '_Balanced_v2','_Normal_v2']
        extension2 = ["_RR", "_RA"]
        for filename in problem_list:
            for ext in extension:
                for ext2 in extension2:
                    # solve_problem(problem_set, filename)
                    name = (
                        "Prelim_test_output/"
                        + problem_set
                        + "/"
                        + filename[: -len("_problem_info.dat")]
                        + ext2
                        + ext
                        + ".csv"
                    )
                    info = return_problem_data(problem_set, filename)
                    # info.maxTrip = 21600#3*info.maxTrip
                    NNS = EPS_IF(info)
                    NNS.write_output = True
                    NNS.file_write = open(name, "w")
                    if (ext == "_Balanced_NR") | (ext == "_Normal_NR"):
                        NNS.reduce_all_trips = False
                    if (ext == "_Balanced_v2") | (ext == "_Normal_v2"):
                        NNS.reduce_all_trips = True
                    if (ext == "_Balanced_NR") | (ext == "_Balanced_v2"):
                        balanced = True
                    if (ext == "_Normal_NR") | (ext == "_Normal_v2"):
                        balanced = False
                    if ext2 == "_RR":
                        NNS.EPS_IF_solver(
                            rule_type="EPS_IF_random_five_rules",
                            nSolutions=200,
                            balanced=balanced,
                        )
                    if ext2 == "_RA":
                        NNS.EPS_IF_solver(
                            rule_type="EPS_random_arc",
                            nSolutions=200,
                            balanced=balanced,
                        )
                    NNS.file_write.close()


if __name__ == "__main__":
    pass
#     # key print('Use profile_path_scanning to test the algorithm')
#     problem_set = 'Lpr_IF'
#     filename = 'Lpr_IF-a-05_problem_info.dat'
#     # key print('')
#     # key print('Test extended path scanning on ' + filename)
#     # key print('')
#     # key print('Read problem data')
#     info = return_problem_data(problem_set, filename)
#     eps = EPS_MultipleGiantRoute(info)
#     # key print('Test balanced extended path scanning on ' + filename)
#     # key print('')
#     # key print('Solve problem')
#     # key print('')
#     s = eps.EPS_IF_all_rules_IFs(balanced=True)
#     # key print(s)
# cProfile.run("eps.EPS_IF_five_rules(balanced=True)", sort=1)
