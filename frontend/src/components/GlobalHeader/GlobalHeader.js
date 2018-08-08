import React,{ Component } from 'react';
import moment from 'moment';
import groupBy from 'lodash/groupBy';
import Debounce from 'lodash-decorators/debounce';
import { Menu, Icon,Tag, Dropdown, Avatar, Divider, Tooltip } from 'antd';
import classNames from 'classnames';

import HeaderSearch from '../HeaderSearch/HeaderSearch';
import NoticeIcon from '../NoticeIcon/NoticeIcon';

import styles from '../../assets/less/components/globalHeader.less'

export default class GlobalHeader extends Component {

    componentWillUnmount(){
        this.triggerResizeEvent.cancel();
    }

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
        this.triggerResizeEvent();
    }
    /* */
    @Debounce(600)
    triggerResizeEvent(){
        const event = document.createElement('HTMLEvents');
        event.initEvent('resize',true, false);
        window.dispatchEvent(event);
    };

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
            <Menu className = {styles.menu} selectedKeys = {[]} onClick = {onMenuClick}>
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
            <div className = {styles.header}>
                {isMobile && [
                <div className = {styles.logo} key = "logo">
                    <img src = {logo} alt = "logo" width = "32"/>
                </div>
                <Divider type = "vertical" key = "line" />
                ]}
                <Icon 
                    className = {styles.trigger}
                    type = { collapsed ? 'menu-unfold' : 'menu-fold'}
                    onClick = { this.toggle }
                />
                <div className = {styles.right}>
                    <HeaderSearch 
                        className = { `${styles.action} ${styles.search}`}
                        placeholder = "search"
                        datasource = {[]}
                        onSearch = { value => {
                            console.log('input',value);
                        }}
                        onPressEnter = {value => {
                            console.log('enter',value);
                        }}
                    />
                    <Tooltip title = "search">
                        <a
                            target = "_blank"
                            href = "#"
                            rel = "noopener noferrer"
                            className = { styles.action }
                        >
                            <Icon type = "question-circle-o"/>
                        </a>
                    </Tooltip>
                    <NoticeIcon
                        className = { styles.action }
                        count = { currentUser.notifyCount }
                        onItemClick = {(item, tabProps) => {
                            console.log(item, tabProps);
                        }}
                        onClear = {onNoticeClear}
                        onPopupVisiblechange = {onNoticeVisibleChange}
                        loading = {fetchingNotices}
                        popupAlign = {{ offset : [20, -16] }}
                    >
                        <NoticeIcon.Tab 
                            list = {noticeData['Notice']}
                            title = 'Notice'
                            emptyText = "You have viewed all notifications"
                            emptyImage = "https://gw.alipayobjects.com/zos/rmsportal/wAhyIChODzsoKIOBHcBk.svg"
                        />
                        <NoticeIcon.Tab 
                            list = {noticeData['Notice']}
                            title = 'Notice'
                            emptyText = "You have viewed all notifications"
                            emptyImage = "https://gw.alipayobjects.com/zos/rmsportal/wAhyIChODzsoKIOBHcBk.svg"
                        />
                        <NoticeIcon.Tab 
                            list = {noticeData['Notice']}
                            title = 'Notice'
                            emptyText = "You have viewed all notifications"
                            emptyImage = "https://gw.alipayobjects.com/zos/rmsportal/wAhyIChODzsoKIOBHcBk.svg"
                        />
                    </NoticeIcon>
                    {currentUser.name ? (
                        <Dropdown overlay = {menu}>
                            <span className =  {`${styles.action} ${styles.account}`}>
                                <Avatar size = "small" className = {styles.avatar} src = {currentUser.avatar}/>
                                <span className = {styles.name}>{currentUser.name}</span>
                            </span>
                        </Dropdown>
                    ) : (
                        <Spin size = "small" style = {{ marginLeft : 8 }}/>
                    )}
                </div>
            </div>
        );
    }
}