import React,{Component} from 'react';
import {Layout,Menu,Icon,SubMenu,message} from 'antd';
import { enquireScreen, unenquireScreen } from 'enquire-js';

import SiderMenu from '../../components/SiderMenu/SiderMenu';
import GlobalHeader from '../../components/GlobalHeader/GlobalHeader';


import '../../assets/css/containers/layout.css';

const {Header,Sider,Content} = Layout;

let isMobile;
enquireScreen(b => {
    isMobile : b;
});

class BaseLayout extends Component{
    state = {
        isMobile,
    };

    toggle = () => {
        this.setState({
            collapsed : !this.state.collapsed,
        });
    }

    componentDidMount(){
        this.enquireHandler = enquireScreen(mobile => {
            this.setState({
                isMobile :  mobile,
            });
        });
    }

    componentWillUnmount(){
        unenquireScreen(this.enquireHandler);
    }

    handleMenuCollapse = collapsed => {
        
    };

    handleNoticeClear = type => {
        message.success(`Emptied${type}`);
    };

    handleMenuClick = ({ key }) => {

    }

    handleNoticeVisibleChange = visible => {

    }

    render(){
        const {
            currentUser,
            collapsed,
            fetchingNotices,
            notices,
            routerData,
            match,
            location,
        } = this.props;
        
        const { isMobile: mb } = this.state;
        return(
            <Layout>
                <SiderMenu />
                <Layout>
                    <Header style = {{padding : 0 }}>
                        <GlobalHeader 
                            logo = {logo}
                            currentUser = {currentUser}
                            fetchingNotices = {fetchingNotices}
                            notices = {notices}
                            collapsed = {collapsed}
                            isMobile = {mb}
                            onNoticeclear = {this.handleNoticeClear}
                            onCollapse = {this.handleMenuCollapse}
                            onMenuclick = {this.handleMenuClick}
                            onNoticeVisibleChange = {this.handleNoticeVisibleChange}
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