import * as ActionTypes from './Actions';
import Axios from 'axios';

const squel = require('squel');

export const workspaceAdd = (workspaceName) => {
    return {
        type : ActionTypes.WORKSPACE_ADD,
        workspaceName : workspaceName
    }
}

export const fieldAdd = fields => {
    return {
        type : ActionTypes.FIELD_ADD,
        fields : fields
    }
}

export const joinDataAdd = joinData => {
    return {
        type : ActionTypes.JOIN_DATA_ADD,
        joinData : joinData,
    }
}

export const tableAdd = table => {
    return {
        type : ActionTypes.TABLE_ADD,
        table : table
    }
}

// export const datasetName = name => {
//     return {
//         type : ActionTypes.SAVE_DATASET_NAME,
//         name : name
//     }
// }

const saved = (name) => {
    return {
        type : ActionTypes.SAVED
    }
}

const saveError = error => {
    return {
        type : ActionTypes.SAVE_ERROR,
        error : error
    }
}

const loginSuccess = data => {
    if(data.status){
        return {
            type : ActionTypes.LOGIN_SUCCESS,
            data : data.data
        }
    }
}

const loginError = error => {
    return {
        type : ActionTypes.LOGIN_ERROR,
        error : error
    }
}

const save = (name,state) => {
    return dispatch => {
        const postData = {
            url : `${process.env.REACT_APP_API_URL}/datasets/`,
            method : 'POST',
            data : JSON.stringify({
                name : name,
                fields : state().dataset.fields,
                tables : state().dataset.tables,
                joins : state().dataset.joins,
                mode : state().dataset.sqlMode,
                sql : state().dataset.sql,
            }),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        return Axios(postData).then((res) => dispatch(saved(name))).catch(e => dispatch(saveError(e)));
    }
}

const validate = loginData => {
    return dispatch => {
        const postData = {
            url : 'http://pragyaambackend.mysnippt.com/api/login',
            method : 'POST',
            data : JSON.stringify({
                ...loginData
            }),
            headers : { 'Content-Type' : 'application/json'}
        }
        return Axios(postData).then(res => dispatch(loginSuccess(res.data))).catch( e => dispatch(loginError(e)));
    }
}

export const saveDataset = (name) => {
    return (dispatch,getState) => dispatch(save(name,getState))
}

export const login = (loginData) => {
    return (dispatch,getState) => dispatch(validate(loginData))
}

export const fieldClear = () => {
    return (dispatch,getState) => dispatch(saveError("error"))
}

export const mobileResizeFunction = () => {
    if(window.innerWidth > 960){
        return {
            type : ActionTypes.MOBILE_RESIZE,
            mobileOpen : false
        }
    }
}

export const handleDrawerToggle = () => {
    return {
        type : ActionTypes.DRAWER_TOGGLE
    }
}

export const handleDrawerToggleOnUpdate = () => {
    return {
        type : ActionTypes.DRAWER_TOGGLE_ON_UPDATE,
        mobileOpen : false
    }
}

export const handleMiniSidebarToggle = () => {
    return {
        type : ActionTypes.SIDEBAR_MINI_TOGGLE
    }
}

// export const getDefaultGraphData = (name) => {
//     return {
//         type : ActionTypes.GRAPH_DEFAULT,
//         name : name
//     }
// }

const loadSuccess = (data, options) => {
    delete options.type;
    return {
        type : ActionTypes.DATA_LOAD,
        data : data,
        options : options
    }
}

const loadError = err => {
    return {
        type : ActionTypes.DATA_LOAD_ERROR,
        error : err
    }
}

const loadData = data => {
    return dispatch => {
        const postData = {
            url : `${process.env.REACT_APP_API_URL}/report_generate/`,
            method : 'POST',
            data : JSON.stringify(data),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => dispatch(loadSuccess(res.data.data, data)))
            .catch(err => dispatch(loadError(err)));
    }
} 

export const handleDataLoad = (data) => {
    return (dispatch,getState) => (dispatch(loadData(data)))
}

export const handleDefaultDataLoad = (data,type) => {
    return {
        type : ActionTypes.DEFAULT_DATA_LOAD,
        data : data.data,
        options : {
            type: type,
            reportOptions : data.options
        }
    }
}

export const handleClearReportData = () => {
    return { 
        type : ActionTypes.DATA_LOAD_ERROR
    }
}

const dashLoadSuccess = (data, id) => {
    return {
        type : ActionTypes.DASH_LOAD_DATA,
        data : data,
        id : id
    }
}

const dashLoadError = (err) => {
    return {
        type : ActionTypes.DASH_LOAD_ERROR,
        error : err
    }
}

const reportLoadSuccess = (data, id) => {
    return {
        type : ActionTypes.REPORT_LOAD_DATA,
        data : data,
        id : id
    }
}

const reportLoadError = (err) => {
    return {
        type : ActionTypes.REPORT_LOAD_ERROR,
        errror : err
    }
}

const dashLoadData = (data, id) => {
    return dispatch => {
        const postData = {
            url : `${process.env.REACT_APP_API_URL}/report_generate/`,
            method : 'POST',
            data : JSON.stringify(data.report_options),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => dispatch(dashLoadSuccess(res.data.data, id)))
            .catch(err => dispatch(dashLoadError(err)));
    }
}

const reportLoadData = (data,id) => {
    return dispatch => {
        const postData = {
            url : `${process.env.REACT_APP_API_URL}/report_generate/`,
            method : 'POST',
            data : JSON.stringify(data.report_options),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => dispatch(reportLoadSuccess(res.data.data, id)))
            .catch(err => dispatch(reportLoadError(err)));
    }
}

export const handleDashCustomizeFetchData = (data, id) => {
    return (dispatch,getState) => (dispatch(dashLoadData(data, id)));
}

export const clearDashCustomizeData = () => {
    return {
        type : ActionTypes.DASH_LOAD_ERROR
    }
}

export const handleReportFetchData = (data,id) => {
    return (dispatch,getState) => (dispatch(reportLoadData(data, id)));
}

export const clearReportDataList = () => {
    return {
        type : ActionTypes.REPORT_LOAD_ERROR
    }
}

const saveSql = (sql) => {
    return {
        type : ActionTypes.SAVE_SQL,
        sql : sql, 
    }
}

const generateSql = (state) => {
    return dispatch => {
        let queryResult = '';
        let count = 0;
        let flag = 0;
        state().dataset.tables.forEach(table => {
            flag = 0;
            let queryGenerate = '';
            state().dataset.joins.forEach(join => {
                if(table.name === join.worksheet_1 || table.name === join.worksheet_2){
                    flag = 1;
                }
            });
            if(!flag){
                console.log(table);
                queryGenerate = squel.useFlavour('postgres').select({ autoQuoteTableNames: true, autoQuoteFieldNames: true }).from(table.name);
                state().dataset.fields.filter(item => item.key === table.name).forEach( field => {
                    queryGenerate = queryGenerate.field(field.name);
                });
                queryGenerate = queryGenerate.toString();
                count += 1;
            
            console.log(queryGenerate)
            if(count > 1){
                queryResult = queryResult.slice(0,-1);
                queryResult = queryResult.concat(" UNION ALL ", queryGenerate, ";");
            }
            else {
                queryResult = queryResult.concat(queryGenerate, ";");
            }
        }
        });
        state().dataset.joins.forEach( join => {
            let queryGenerate = '';
            switch(join.type){
                case "Inner-Join":
                    queryGenerate = squel.useFlavour('postgres').select({ autoQuoteTableNames: true, autoQuoteFieldNames: true }).from(join.worksheet_1).join(join.worksheet_2, null, `${"`"}${join.worksheet_1}${"`"}.${"`"}${join.field}${"`"} = ${"`"}${join.worksheet_2}${"`"}.${"`"}${join.field}${"`"}`);
                    count += 1;
                    break;
                case "Right-Join":
                    queryGenerate = squel.useFlavour('postgres').select({ autoQuoteTableNames: true, autoQuoteFieldNames: true }).from(join.worksheet_1).right_join(join.worksheet_2, null, `"${join.worksheet_1}"."${join.field}" = "${join.worksheet_2}"."${join.field}"`);
                    count += 1;
                    break;
                case "Left-Join":
                    queryGenerate = squel.useFlavour('postgres').select({ autoQuoteTableNames: true, autoQuoteFieldNames: true }).from(join.worksheet_1).left_join(join.worksheet_2, null, `"${join.worksheet_1}"."${join.field}" = "${join.worksheet_2}"."${join.field}"`);
                    count += 1;
                    break;
                case "Outer-Join":
                    queryGenerate = squel.useFlavour('postgres').select({ autoQuoteTableNames: true, autoQuoteFieldNames: true }).from(join.worksheet_1).outer_join(join.worksheet_2, null, `"${join.worksheet_1}"."${join.field}" = "${join.worksheet_2}"."${join.field}"`);
                    count += 1;
                    break;
            };
            state().dataset.fields.filter(item => item.key === join.worksheet_1 || item.key === join.worksheet_2).forEach( field => {
                if(join.field !== field.name) queryGenerate = queryGenerate.field(`${field.key}.${field.name}`);
                else {
                    switch(join.type){
                        case "Inner-Join":
                            queryGenerate = queryGenerate.field(`${join.worksheet_1}.${field.name}`);
                            break;
                        case "Right-Join":
                            queryGenerate = queryGenerate.field(`${join.worksheet_2}.${field.name}`);
                            break;
                        case "Left-Join":
                            queryGenerate = queryGenerate.field(`${join.worksheet_1}.${field.name}`);
                            break;
                        case "Outer-Join":
                            queryGenerate = queryGenerate.field(`${join.worksheet_1}.${field.name}`);
                            break;
                    }
                }
            });
            queryGenerate = queryGenerate.toString();
            if(count > 1){
                console.log(count);
                queryResult = queryResult.slice(0,-1);
                queryResult = queryResult.concat(" UNION ALL ", queryGenerate, ";")
            }
            else {
                queryResult = queryResult.concat(queryGenerate, ";");
            }
        })
        return dispatch(saveSql(queryResult));
    }
}

export const getCurrentSql = () => {
    return (dispatch, getState) => dispatch(generateSql(getState))
    
}

export const changeCurrentMode = () => {
    return {
        type : ActionTypes.CHANGE_SQL_EDIT_MODE,
    }
}