import React,{Component} from 'react';
import {Layout,Menu,Icon,SubMenu} from 'antd';

import SiderMenu from '../../components/SiderMenu/SiderMenu';

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
                <SiderMenu />
                <Layout>
                    <Header style = {{padding : 0 }}>
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