import Dashboard from '../layouts/Dashboard/Dashboard';
import Auth from '../layouts/Auth';

const indexRoutes = [
    {
        path: '/auth',
        component: Auth
    },
    { 
        path : '/', 
        component : Dashboard 
    }
];

export default indexRoutes;