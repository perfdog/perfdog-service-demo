# -*- coding: utf-8 -*-
import subprocess
import time
import traceback

import grpc
import perfdog_pb2_grpc
import perfdog_pb2
import threading


# 第一次运行demo前需要通过pip安装grpcio(1.23.0)和protobuf(3.10.0)
def run():
    try:
        # 在代码里启动PerfDogService或手动启动PerfDogService
        print("0.启动PerfDogService")
        # 填入PerfDogService的路径
        perfDogService = subprocess.Popen('-')
        # 等待PerfDogService启动完毕
        time.sleep(5)
        print("1.通过ip和端口连接到PerfDog Service")
        options = [('grpc.max_receive_message_length', 100 * 1024 * 1024)]
        channel = grpc.insecure_channel('127.0.0.1:23456', options=options)
        print("2.新建一个stub,通过这个stub对象可以调用所有服务器提供的接口")
        stub = perfdog_pb2_grpc.PerfDogServiceStub(channel)
        print("3.通过令牌登录，令牌可以在官网申请")
        userInfo = stub.loginWithToken(perfdog_pb2.Token(token='-'))
        print("UserInfo:\n", userInfo)
        print("4.启动设备监听器监听设备,每当设备插入和移除时会收到一个DeviceEvent")
        deviceEventIterator = stub.startDeviceMonitor(perfdog_pb2.Empty())
        for deviceEvent in deviceEventIterator:
            # 从DeviceEvent中获取到device对象，device对象会在后面的接口中用到
            device = deviceEvent.device
            if deviceEvent.eventType == perfdog_pb2.ADD:
                print("设备[%s:%s]插入\n" % (device.uid, perfdog_pb2.DEVICE_CONTYPE.Name(device.conType)))
                # 每台手机会返回两个conType不同的设备对象(USB的和WIFI的),如果是测有线，取其中的USB对象
                if device.conType == perfdog_pb2.USB:
                    print("5.初始化设备[%s:%s]\n" % (device.uid, perfdog_pb2.DEVICE_CONTYPE.Name(device.conType)))
                    stub.initDevice(device)
                    print("6.获取app列表")
                    appList = stub.getAppList(device)

                    #
                    apps = appList.app
                    app_index = 0
                    for app in apps:
                        print('%s: %s->%s' % (app_index, app.label, app.packageName))
                        app_index += 1

                    app_select = int(input("请选择要测试App: "))
                    app = apps[app_select]

                    print("7.获取设备的详细信息")
                    deviceInfo = stub.getDeviceInfo(device)
                    print("8.开启性能数据项")
                    stub.enablePerfDataType(
                        perfdog_pb2.EnablePerfDataTypeReq(device=device, type=perfdog_pb2.NETWORK_USAGE))
                    print("9.开始收集[%s:%s]的性能数据\n" % (app.label, app.packageName))
                    print(stub.startTestApp(perfdog_pb2.StartTestAppReq(device=device, app=app)))

                    req = perfdog_pb2.OpenPerfDataStreamReq(device=device)
                    perfDataIterator = stub.openPerfDataStream(req)

                    def perf_data_process():
                        for perfData in perfDataIterator:
                            print(perfData)

                    threading.Thread(target=perf_data_process).start()
                    # 采集一些数据
                    time.sleep(20)
                    print("10.设置label")
                    stub.setLabel(perfdog_pb2.SetLabelReq(device=device, label="I am a label"))
                    time.sleep(3)
                    print("11.添加批注")
                    stub.addNote(perfdog_pb2.AddNoteReq(device=device, time=5000, note="I am a note"))
                    print("12.上传和导出所有数据")
                    saveResult = stub.saveData(perfdog_pb2.SaveDataReq(
                        device=device,
                        caseName="case1",  # web上case和excel的名字
                        uploadToServer=True,  # 上传到perfdog服务器
                        exportToFile=True,  # 保存到本地
                        outputDirectory="F:\\perfdog_service_output\\",
                        dataExportFormat=perfdog_pb2.EXPORT_TO_JSON
                    ))

                    print("保存结果:\n", saveResult)
                    print("12.上传和导出第5秒到20秒的数据")
                    stub.saveData(perfdog_pb2.SaveDataReq(
                        device=device,
                        beginTime=5000,  # 指定开始时间
                        endTime=20000,  # 指定结束时间
                        caseName="case2",  # web上case和excel的名字
                        uploadToServer=True,  # 上传到perfdog服务器
                        exportToFile=True,  # 保存到本地
                        outputDirectory="F:\\perfdog_service_output\\",
                        dataExportFormat=perfdog_pb2.EXPORT_TO_EXCEL
                    ))
                    print("13.停止测试")
                    stub.stopTest(perfdog_pb2.StopTestReq(device=device))
                    print("over")
                    break
            elif deviceEvent.eventType == perfdog_pb2.REMOVE:
                print("设备[%s:%s]移除\n" % (device.uid, perfdog_pb2.DEVICE_CONTYPE.Name(device.conType)))
    except Exception as e:
        traceback.print_exc()


if __name__ == '__main__':
    run()
