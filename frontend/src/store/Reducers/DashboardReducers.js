import * as ActionTypes from '../Actions/Actions';

const DashboardHandler = (state = { dashreportCustomize : [] }, action) => {
    switch(action.type){
        case ActionTypes.DASH_LOAD_DATA:
            return {
                ...state,
                dashreportCustomize : [...state.dashreportCustomize,{id : action.id, data : action.data}]
            }
        default:
            return {
                ...state
            }
    }
}

export default DashboardHandler;