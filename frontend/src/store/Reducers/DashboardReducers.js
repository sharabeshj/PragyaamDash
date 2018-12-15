import * as ActionTypes from '../Actions/Actions';

const DashboardHandler = (state = { dashReportCustomize : [] }, action) => {
    switch(action.type){
        case ActionTypes.DASH_LOAD_DATA:
            return {
                ...state,
                dashReportCustomize : [...state.dashReportCustomize,{id : action.id, data : action.data}]
            }
        default:
            return {
                ...state
            }
    }
}

export default DashboardHandler;