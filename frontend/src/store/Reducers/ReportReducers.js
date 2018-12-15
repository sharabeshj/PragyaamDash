import * as ActionTypes from '../Actions/Actions';

const ReportHandler = (state = { reportData : {}, report_id : '', options : {} }, action) => {
    switch(action.type){
        case ActionTypes.DATA_LOAD:
            return {
                ...state,
                reportData : {...action.data},
                options : {
                    ...action.options
                }

            }
        case ActionTypes.DATA_LOAD_ERROR:
            return {
                ...state,
                reportData : {}
            }
        default:
            return state;
    }
}

export default ReportHandler;