import * as ActionTypes from '../Actions/Actions';

const DatasetHandler = (state = { fields : [], joins : []}, action) => {
    switch(action.type){
        case ActionTypes.WORKSPACE_ADD:
            return {
                ...state.dataset,
                    workspace : action.workspaceName
            }
        case ActionTypes.FIELD_ADD:
            return {
                ...state,
                fields : action.fields
            }

        case ActionTypes.SAVED:
            return {
                ...state,
                joins : action.joins
            }

        case ActionTypes.SAVE_ERROR:
            return {
                ...state,
                fields : [],
                joins : []
            }
        default:
            return state;
    }
}

export default DatasetHandler;