import React,{ Component } from 'react';
import moment from 'moment';
import groupBy from 'loadash/groupBy';
import { Menu, Icon,Tag, Dropdown, Avatar, Divider, Tooltip } from 'antd';
import classNames from 'classnames';

export default class GlobalHeader extends Component {
    getNoticeData() {
        const { notices } = this.props;
        if(notices === null || notices.length === 0){
            return {};
        }
        const newNotices = notices.map(notice => {
            const newNotice = { ...notice };
            if(newNotice.datetime){
                newNotice.datetime = moment(notice.datetime).fromNow();
            }
            if(newNotice.id){
                newNotice.key = newNotice.id;
            }
            if(newNotice.extra && newNotice.status){
                const color = {
                    todo : '',
                    processing : 'blue',
                    urgent : 'red',
                    doing : 'gold',
                }[newNotice.status];
                newNotice.extra = (
                    <Tag color = {color} style = {{ marginRight : 0 }}>
                        {newNotice.extra}
                    </Tag>
                );
            } 
            return newNotice;
        });
        return groupBy(newNotices,'type');
    }

    toggle = () => {
        const { collapsed,onCollapse } = this.props;
        onCollapse(!collapsed);
    }
    render() {
        const {
            currentUser = {},
            collapsed,
            fetchingNotices,
            isMobile,
            logo,
            onNoticeVisibleChange,
            onMenuClick,
            onNoticeClear,
        } = this.props;

        const menu = (
            <Menu className = "menu" selectedKeys = {[]} onClick = {onMenuClick}>
                <Menu.Item disabled>
                    <Icon type = "user"/>Profile
                </Menu.Item>
                <Menu.Item disabled>
                    <Icon type = "setting"/>Setting
                </Menu.Item>
                <Menu.Item key = "logout">
                    <Icon type = "logout"/>Log Out
                </Menu.Item>
            </Menu>
        );

        const noticeData = this.getNoticeData();

        return(
            <div className = "header">
                {isMobile && [
                <div className = "logo" key = "logo">
                    <img src = "" alt = "logo" width = "32"/>
                </div>
                <Divider type = "vertical" key = "line" />
                ]}
                <Icon 
                    className = "trigger"
                    type = { collapsed ? 'menu-unfold' : 'menu-fold'}
                    onClick = { this.toggle }
                />
                <div className = "right">
                    
                </div>
            </div>
        )
    }
}