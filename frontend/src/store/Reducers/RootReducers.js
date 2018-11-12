import { combineReducers } from 'redux';

import DatasetHandler from './DatasetReducers';
import LoginHandler from './LoginReducers';
import DrawerHandler from './DrawerReducer';

const RootReducers = combineReducers({
    dataset : DatasetHandler,
    login : LoginHandler,
    drawer : DrawerHandler
});

export default RootReducers;