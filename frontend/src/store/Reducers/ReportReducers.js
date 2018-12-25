import * as ActionTypes from '../Actions/Actions';

const ReportHandler = (state = { reportData : {}, report_id : '', options : {}, reportDataList : [] }, action) => {
    switch(action.type){
        case ActionTypes.DATA_LOAD:
            return {
                ...state,
                reportData : {...action.data},
                options : {
                    ...state.options,
                    ...action.options,
                    reportOptions : {
                        ...state.options.reportOptions,
                        title : {
                            ...state.options.reportOptions.title,
                            text : action.options.reportDescription
                        }
                    }
                }

            }
        case ActionTypes.DEFAULT_DATA_LOAD:
            return {
                ...state,
                reportData : { ...action.data },
                options : { ...action.options }
            }
        case ActionTypes.DATA_LOAD_ERROR:
            return {
                ...state,
                reportData : {}
            }
        case ActionTypes.REPORT_LOAD_DATA:
            return {
                ...state,
                reportDataList : [...state.reportDataList, { id : action.id, data : action.data }]
            }
        case ActionTypes.REPORT_LOAD_ERROR:
            return {
                ...state,
                reportDataList : []
            }
        default:
            return state;
    }
}

export default ReportHandler;