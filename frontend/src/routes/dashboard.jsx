import Storage from '@material-ui/icons/Storage';
import PhotoFilter from '@material-ui/icons/PhotoFilter';
import Home from '@material-ui/icons/Home';
import TableChart from '@material-ui/icons/TableChart';
import Layer from '@material-ui/icons/Layers'

import Dataset from '../views/Dataset/Dataset';
import Report from '../views/Report/Report';
import HomePage from '../views/HomePage/HomePage';
import WorkspacePage from '../views/WorkspacePage/WorkspacePage';
import Layers from '../views/Layers/Layers';



const dashboardRoutes = [
  {
    path: "/home",
    sidebarName: "Home",
    navbarName: "Home",
    icon:Home,
    component:HomePage
  },
  { 
    path: "/workspace",
    sidebarName: "Workspace",
    navbarName: "Workspace",
    icon: TableChart,
    component: WorkspacePage    
  },
  {
    path: "/dataset",
    sidebarName: "Dataset",
    navbarName: "Dataset",
    icon: Storage,
    component: Dataset
  },
  {
    path: "/layer",
    sidebarName: "Layers",
    navbarName: "Layers",
    icon: Layer,
    component: Layers
  },
  {
    path: "/report",
    sidebarName: "Report",
    navbarName: "Report",
    icon: PhotoFilter,
    component: Report
  },
  // { redirect: true, path: "/", to: "/dashboard", navbarName: "Redirect" }
];

export default dashboardRoutes;
