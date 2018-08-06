import React,{Component} from 'react';
import {Layout,Menu,Icon,SubMenu} from 'antd';
import '../../assets/css/containers/layout.css';

const {Header,Sider,Content} = Layout;



class BaseLayout extends Component{
    state = {
        collapsed : false,
    };

    toggle = () => {
        this.setState({
            collapsed : !this.state.collapsed,
        });
    }

    render(){
        return(
            <Layout>
                <Sider
                    trigger = {null}
                    collapsible
                    collapsed = {true}
            
                >
                    <div className = "logo" />
                    <Menu theme = "dark" mode = "vertical" defaultSelectedkeys = {['home']}>
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
                <Layout>
                    <Header style = {{ background : '#fff', padding : 0 }}>
                        <Icon 
                            className = "trigger"
                            type = { this.state.collapsed ? 'menu-unfold' : 'menu-fold'}
                            onClick = { this.toggle }
                        />
                    </Header>
                    <Content className = "content" >
                        Content
                    </Content>
                </Layout>
            </Layout>
        );
    }
}

export default BaseLayout;