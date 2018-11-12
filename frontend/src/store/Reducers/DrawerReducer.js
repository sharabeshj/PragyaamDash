import * as ActionTypes from '../Actions/Actions';

const DrawerHandler = (state = { mobileOpen : false },action) => {
    switch(action.type){
        case ActionTypes.MOBILE_RESIZE:
            return {
                ...state,
                mobileOpen : action.mobileOpen
            }
        case ActionTypes.DRAWER_TOGGLE:
            return {
                ...state,
                mobileOpen : !state.mobileOpen
            }
        case ActionTypes.DRAWER_TOGGLE_ON_UPDATE:
            return {
                ...state,
                mobileOpen : action.mobileOpen
            }
        default:
            return {
                ...state
            }
    }
}

export default DrawerHandler;