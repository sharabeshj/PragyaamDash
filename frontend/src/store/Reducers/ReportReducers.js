import * as ActionTypes from '../Actions/Actions';

const ReportHandler = (state = { reportData : {}, report_id : '' }, action) => {
    switch(action.types){
        case ActionTypes.DATA_LOAD:
            return {
                ...state,
                reportData : {...action.data}
            }
        case ActionTypes.DATA_LOAD_ERROR:
            return {
                ...state,
                reportData : { error : action.error }
            }
        default:
            return state;
    }
}

export default ReportHandler;