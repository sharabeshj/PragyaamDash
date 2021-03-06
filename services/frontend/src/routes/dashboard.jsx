import Storage from '@material-ui/icons/Storage';
import PhotoFilter from '@material-ui/icons/PhotoFilter';
import Home from '@material-ui/icons/Home';
import TableChart from '@material-ui/icons/TableChart';
import Layer from '@material-ui/icons/Layers'

import CreateDataset from '../views/Dataset/CreateDataset/CreateDataset';
import DatasetList from '../views/Dataset/DatasetList/DatasetList';
import ReportCreate from '../views/Report/ReportCreate/ReportCreate';
import ReportList from '../views/Report/ReportList/ReportList';
import HomePageCustomize from '../views/HomePage/HomePageCustomize/HomePageCustomize';
import HomePageDisplay from '../views/HomePage/HomePageDisplay/HomePageDisplay';
import WorkspacePage from '../views/WorkspacePage/WorkspacePage';
import Layers from '../views/Layers/Layers';
import Login from '../views/Login';


const dashboardRoutes = [
  {
    collapse : "true",
    path: "/home",
    name: "Dashboard",
    icon:Home,
    views : [
      {
        path: "/home/customize",
        name: "Dashboard Customize",
        mini : "DC",
        component : HomePageCustomize,
        icon:Home
      },
      {
        path: "/home",
        name: "Dashboard",
        mini: "D",
        component: HomePageDisplay,
        icon:Home
      }
    ]
  },
  { 
    path: "/workspace",
    name: "Workspace",
    icon: TableChart,
    component: WorkspacePage    
  },
  {
    collapse: true,
    path: "/datasets",
    name: "Dataset",
    state: "openDatasets",
    icon: Storage,
    views: [
      {
        path: "/datasets/create",
        name: "Create Dataset",
        mini: "CD",
        component: CreateDataset
      },
      {
        path: "/datasets/list",
        name: "Dataset List",
        mini: "DL",
        component: DatasetList
      }
    ]
  },
  {
    path: "/layer",
    name: "Layer",
    icon: Layer,
    component: Layers
  },
  {
    collapse: true,
    path: "/reports",
    name: "Reports",
    icon: PhotoFilter,
    views: [
      {
        path: "/reports/create",
        name: "Create Report",
        mini: "CR",
        component: ReportCreate
      },
      {
        path: "/reports/list",
        name: "Report List",
        mini: "RL",
        component: ReportList
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    layout: '/auth'
  },
  // {
  //   path: '/logout',
  //   name: 'Logout',
  //   component: 
  // },
  { redirect: true, path: "/", to: "/home", navbarName: "Redirect" }
];

export default dashboardRoutes;
