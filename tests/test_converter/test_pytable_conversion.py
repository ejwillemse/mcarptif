import pickle
from solver.solve import gen_solution
from solver.solve import initiate_tabu_search
from solver.solve import clear_improvement_setup
from solver.solve import improve_solution
from solver.solve import solve_instance
from solver.solve import solve_store_instance


class Info:
    def __init__(self):
        pass

info = Info()

test_file = '../../../waste_labs_sandbox/alba_pungol_city_tender_hl/temp/info_test.dat'
with open(test_file, 'rb') as f:
    infoList = pickle.load(f)

    [
        info.nArcs,
        info.depotnewkey,
        info.IFarcsnewkey,
        info.dumpCost,
        info.if_cost_np,
        info.if_arc_np,
        info.travelCostL,
        info.demandL,
        info.maxTrip,
        info.capacity,
        info.nn_list,
        info.demandL,
        info.serveCostL,
        info.if_cost_np,
        info.if_arc_np,
        info.d,
        info.reqInvArcList,
        info.reqArcsPure,
        info.reqEdgesPure,
        info.reqArcListActual,
        info.reqArcList,
        info.name,
        info.p_full,
        info.allIndexD
    ] = infoList

    solution_df = solve_store_instance('', improve='TS', write_results=False,
                                       info=info, overwrite=True,
                                       test_solution=True)
