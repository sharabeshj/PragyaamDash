import * as ActionTypes from '../Actions/Actions';

const DatasetHandler = (state = { name : '', fields : [], joins : [], tables : []}, action) => {
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
        case ActionTypes.TABLE_ADD:
            return {
                ...state,
                tables : [...state.tables,action.table]
            }

        case ActionTypes.SAVED:
            return {
                ...state,
                joins : action.joins,
                name : action.name
            }

        case ActionTypes.SAVE_ERROR:
            return {
                ...state,
                fields : [],
                joins : [],
                name : ''
            }
        default:
            return state;
    }
}

export default DatasetHandler;