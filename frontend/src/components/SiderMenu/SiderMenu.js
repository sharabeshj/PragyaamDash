import React,{ Component } from 'react';
import { Layout,Menu,Icon } from 'antd';

import styles from '../../assets/less/components/siderMenu.less';

const { Sider } = Layout;

export default class SiderMenu extends Component {
    constructor(props){
        super(props);
    };

    render(){
        const { logo } = this.props;
        let selectedKeys = ['home'];
        
        return (
            <Sider
                    trigger = {null}
                    collapsible
                    collapsed = {true}
                    breakpoint = "lg"
                    className = {styles.sider}
            
                >
                    <div className = {styles.logo} key = "logo">
                        <img src="" alt="logo"/>
                    </div>
                    <Menu theme = "dark" mode = "inline" defaultSelectedkeys = {['home']} style = {{ padding : '16px 0', width : '100%' }}>
                        <Menu.Item key = "home" >
                            <Icon style = {{ fontSize : 20 }} type = "home"/>
                            <span>Home</span>
                        </Menu.Item>
                        <Menu.Item key = "worksheet" style = {{ padding : 20 }}>
                            <Icon style = {{ fontSize : 20 }} type = "table"/>
                            <span>Worksheet</span>
                        </Menu.Item>
                        <Menu.Item key = "dataset" style = {{ padding : 20 }}>
                            <Icon style = {{ fontSize : 20 }} type = "database"/>
                            <span>Dataset</span>
                        </Menu.Item>
                        <Menu.Item key = "unknown_1" style = {{ padding : 20 }}>
                            <Icon style = {{ fontSize : 20 }} type = "switcher"/>
                        </Menu.Item>
                        <Menu.Item key = "unknown_2" style = {{ padding : 20 }}>
                            <Icon style = {{ fontSize : 20 }} type = "api"/>
                        </Menu.Item>
                        <Menu.Item key = "dashboard" style = {{ padding : 20 }}>
                            <Icon style = {{ fontSize : 20 }} type = "dashboard"/>
                            <span>Dashboard</span>
                        </Menu.Item>
                        <Menu.Item key = "report" style = {{ padding : 20 }}>
                            <Icon style = {{ fontSize : 20 }} type = "copy"/>
                            <span>Report</span>
                        </Menu.Item>
                    </Menu>
                </Sider>
        )
    }
}

