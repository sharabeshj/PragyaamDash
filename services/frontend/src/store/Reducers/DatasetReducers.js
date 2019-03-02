import * as ActionTypes from '../Actions/Actions';

const DatasetHandler = (state = { name : '', fields : [], joins : [], tables : [], sql: `/* SQL query of the Dataset */`, sqlMode: 'WATCH'}, action) => {
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
                tables : [...state.tables,{ name : action.table }]
            }
        
        case ActionTypes.JOIN_DATA_ADD:
            return {
                ...state,
                joins : action.joinData,
            }
        case ActionTypes.SAVED:
            return {
                ...state,
                fields : [],
                joins : [],
                name : '',
                tables : []
            }

        case ActionTypes.SAVE_ERROR:
            return {
                ...state,
                fields : [],
                joins : [],
                name : '',
                tables : []
            }
        case ActionTypes.CHANGE_SQL_EDIT_MODE:
            return {
                ...state,
                sqlMode : 'EDIT'
            }
        case ActionTypes.SAVE_SQL:
            return {
                ...state,
                sql: action.sql
            }
        default:
            return state;
    }
}

export default DatasetHandler;