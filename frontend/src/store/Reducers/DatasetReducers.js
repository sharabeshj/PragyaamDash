import * as ActionTypes from '../Actions/Actions';

const DatasetHandler = (state = { dataset  : { fields : []}}, action) => {
    switch(action.type){
        case ActionTypes.WORKSPACE_ADD:
            return {
                ...state,
                dataset : {
                    ...state.dataset,
                    workspace : action.workspaceName
                }
            }
        case ActionTypes.FIELD_ADD:
            return {
                ...state,
                dataset : {
                    ...state.dataset,
                    fields : action.fields
                }
            }
        default:
            return state;
    }
}

export default DatasetHandler;