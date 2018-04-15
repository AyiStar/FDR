import tensorflow as tf
import numpy as np
import cv2
import os
import sys
import random
from sklearn.model_selection import train_test_split

def relight(img, alpha=1, bias=0):
    w = img.shape[1]
    h = img.shape[0]
    #image = []
    for i in range(0,w):
        for j in range(0,h):
            for c in range(3):
                tmp = int(img[j,i,c]*alpha + bias)
                if tmp > 255:
                    tmp = 255
                elif tmp < 0:
                    tmp = 0
                img[j,i,c] = tmp
    return img

def get_my_face(pic_num, output_dir, pic_size=64, video=0):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    haar = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    camera = cv2.VideoCapture(video)

    n = 1
    while True:
        if (n <= pic_num):
            print('Processing %s image.' % n)
            # 读帧
            success, img = camera.read()
            cv2.imshow('Video', img)
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = haar.detectMultiScale(gray_img, 1.3, 5)
            for f_x, f_y, f_w, f_h in faces:
                face = img[f_y:f_y+f_h, f_x:f_x+f_w]
                face = cv2.resize(face, (pic_size,pic_size))
                face = relight(face, random.uniform(0.5, 1.5), random.randint(-50, 50))
                cv2.imshow('img', face)
                cv2.imwrite(output_dir+'/'+str(n)+'.jpg', face)
                n += 1
            key = cv2.waitKey(30) & 0xff
            if key == 27:
                break
        else:
            break

def get_other_faces(input_dir, output_dir, pic_size=64):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    haar = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    n = 1
    for (path, dir_names, file_names) in os.walk(input_dir):
        for file_name in file_names:
            if file_name.endswith('.jpg') or file_name.endswith('.JPG'):
                print('Processing picture %s' % n)
                img_path = path+'/'+file_name
                # 从文件读取图片
                img = cv2.imread(img_path)
                # 转为灰度图片
                gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # 使用opencv进行人脸检测 faces为返回的结果
                faces = haar.detectMultiScale(gray_img, 1.3, 5)
                for f_x, f_y, f_w, f_h in faces:
                    face = img[f_y:f_y+f_h, f_x:f_x+f_w]
                    face = cv2.resize(face, (pic_size,pic_size))
                    face = relight(face, random.uniform(0.5, 1.5), random.randint(-50, 50))
                    cv2.imshow('img', face)
                    cv2.imwrite(output_dir+'/'+str(n)+'.jpg', face)
                    n += 1
                key = cv2.waitKey(30) & 0xff
                if key == 27:
                    sys.exit(0)

def getPaddingSize(img):
    h, w, _ = img.shape
    top, bottom, left, right = (0,0,0,0)
    longest = max(h, w)

    if w < longest:
        tmp = longest - w
        # //表示整除符号
        left = tmp // 2
        right = tmp - left
    elif h < longest:
        tmp = longest - h
        top = tmp // 2
        bottom = tmp - top
    else:
        pass
    return top, bottom, left, right

def readData(path, imgs, labs, height, width, max=None):
    if max is None:
        for filename in os.listdir(path):
            if filename.endswith('.jpg'):
                filename = path + '/' + filename

                img = cv2.imread(filename)

                top,bottom,left,right = getPaddingSize(img)
                # 将图片放大， 扩充图片边缘部分
                img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0,0,0])
                img = cv2.resize(img, (height, width))

                imgs.append(img)
                labs.append(path)
    else:
        n = 0
        for filename in os.listdir(path):
            if n >= max:
                break
            n += 1
            if filename.endswith('.jpg'):
                filename = path + '/' + filename

                img = cv2.imread(filename)

                top,bottom,left,right = getPaddingSize(img)
                # 将图片放大， 扩充图片边缘部分
                img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0,0,0])
                img = cv2.resize(img, (height, width))

                imgs.append(img)
                labs.append(path)

def weightVariable(shape):
    init = tf.random_normal(shape, stddev=0.01)
    return tf.Variable(init)

def biasVariable(shape):
    init = tf.random_normal(shape)
    return tf.Variable(init)

def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1,1,1,1], padding='SAME')

def maxPool(x):
    return tf.nn.max_pool(x, ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')

def dropout(x, keep):
    return tf.nn.dropout(x, keep)

def cnnLayer():

    x = tf.placeholder(tf.float32, [None, 64, 64, 3])
    y_ = tf.placeholder(tf.float32, [None, 2])
    keep_prob_5 = tf.placeholder(tf.float32)
    keep_prob_75 = tf.placeholder(tf.float32)

    # 第一层
    W1 = weightVariable([3,3,3,32]) # 卷积核大小(3,3)， 输入通道(3)， 输出通道(32)
    b1 = biasVariable([32])
    # 卷积
    conv1 = tf.nn.relu(conv2d(x, W1) + b1)
    # 池化
    pool1 = maxPool(conv1)
    # 减少过拟合，随机让某些权重不更新
    drop1 = dropout(pool1, keep_prob_5)

    # 第二层
    W2 = weightVariable([3,3,32,64])
    b2 = biasVariable([64])
    conv2 = tf.nn.relu(conv2d(drop1, W2) + b2)
    pool2 = maxPool(conv2)
    drop2 = dropout(pool2, keep_prob_5)

    # 第三层
    W3 = weightVariable([3,3,64,64])
    b3 = biasVariable([64])
    conv3 = tf.nn.relu(conv2d(drop2, W3) + b3)
    pool3 = maxPool(conv3)
    drop3 = dropout(pool3, keep_prob_5)

    # 全连接层
    Wf = weightVariable([8*16*32, 512])
    bf = biasVariable([512])
    drop3_flat = tf.reshape(drop3, [-1, 8*16*32])
    dense = tf.nn.relu(tf.matmul(drop3_flat, Wf) + bf)
    dropf = dropout(dense, keep_prob_75)

    # 输出层
    Wout = weightVariable([512,2])
    bout = weightVariable([2])
    #out = tf.matmul(dropf, Wout) + bout
    out = tf.add(tf.matmul(dropf, Wout), bout)
    return out

def train(my_faces_path, other_faces_path, pic_size=64):

    imgs = []
    labs = []

    readData(my_faces_path, imgs, labs, pic_size, pic_size)
    readData(other_faces_path, imgs, labs, pic_size, pic_size)
    # 将图片数据与标签转换成数组
    imgs = np.array(imgs)
    labs = np.array([[0,1] if lab == my_faces_path else [1,0] for lab in labs])
    # 随机划分测试集与训练集
    train_x,test_x,train_y,test_y = train_test_split(imgs, labs, test_size=0.05, random_state=random.randint(0,100))
    # 参数：图片数据的总数，图片的高、宽、通道
    train_x = train_x.reshape(train_x.shape[0], pic_size, pic_size, 3)
    test_x = test_x.reshape(test_x.shape[0], pic_size, pic_size, 3)
    # 将数据转换成小于1的数
    train_x = train_x.astype('float32')/255.0
    test_x = test_x.astype('float32')/255.0

    print('train size:%s, test size:%s' % (len(train_x), len(test_x)))
    # 图片块，每次取100张图片
    batch_size = 100
    num_batch = len(train_x) // batch_size

    x = tf.placeholder(tf.float32, [None, pic_size, pic_size, 3])
    y_ = tf.placeholder(tf.float32, [None, 2])

    keep_prob_5 = tf.placeholder(tf.float32)
    keep_prob_75 = tf.placeholder(tf.float32)

    # 第一层
    W1 = weightVariable([3,3,3,32]) # 卷积核大小(3,3)， 输入通道(3)， 输出通道(32)
    b1 = biasVariable([32])
    # 卷积
    conv1 = tf.nn.relu(conv2d(x, W1) + b1)
    # 池化
    pool1 = maxPool(conv1)
    # 减少过拟合，随机让某些权重不更新
    drop1 = dropout(pool1, keep_prob_5)

    # 第二层
    W2 = weightVariable([3,3,32,64])
    b2 = biasVariable([64])
    conv2 = tf.nn.relu(conv2d(drop1, W2) + b2)
    pool2 = maxPool(conv2)
    drop2 = dropout(pool2, keep_prob_5)

    # 第三层
    W3 = weightVariable([3,3,pic_size,pic_size])
    b3 = biasVariable([64])
    conv3 = tf.nn.relu(conv2d(drop2, W3) + b3)
    pool3 = maxPool(conv3)
    drop3 = dropout(pool3, keep_prob_5)

    # 全连接层
    Wf = weightVariable([8*16*32, 512])
    bf = biasVariable([512])
    drop3_flat = tf.reshape(drop3, [-1, 8*16*32])
    dense = tf.nn.relu(tf.matmul(drop3_flat, Wf) + bf)
    dropf = dropout(dense, keep_prob_75)

    # 输出层
    Wout = weightVariable([512,2])
    bout = weightVariable([2])
    #out = tf.matmul(dropf, Wout) + bout
    out = tf.add(tf.matmul(dropf, Wout), bout)

    cross_entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=out, labels=y_))

    train_step = tf.train.AdamOptimizer(0.01).minimize(cross_entropy)
    # 比较标签是否相等，再求的所有数的平均值，tf.cast(强制转换类型)
    accuracy = tf.reduce_mean(tf.cast(tf.equal(tf.argmax(out, 1), tf.argmax(y_, 1)), tf.float32))
    # 将loss与accuracy保存以供tensorboard使用
    tf.summary.scalar('loss', cross_entropy)
    tf.summary.scalar('accuracy', accuracy)
    merged_summary_op = tf.summary.merge_all()
    # 数据保存器的初始化
    saver = tf.train.Saver()

    with tf.Session() as sess:

        sess.run(tf.global_variables_initializer())

        summary_writer = tf.summary.FileWriter('./tmp', graph=tf.get_default_graph())
        acc = 0.0
        for n in range(10):
            # 每次取100(batch_size)张图片
            for i in range(num_batch):
                batch_x = train_x[i*batch_size : (i+1)*batch_size]
                batch_y = train_y[i*batch_size : (i+1)*batch_size]
                # 开始训练数据，同时训练三个变量，返回三个数据
                _,loss,summary = sess.run([train_step, cross_entropy, merged_summary_op],
                                           feed_dict={x:batch_x,y_:batch_y, keep_prob_5:0.5,keep_prob_75:0.75})
                summary_writer.add_summary(summary, n*num_batch+i)
                # 打印损失
                print(n*num_batch+i, loss)

                if (n*num_batch+i) % 100 == 0:
                    # 获取测试数据的准确率
                    acc = accuracy.eval({x:test_x, y_:test_y, keep_prob_5:1.0, keep_prob_75:1.0})
                    print(n*num_batch+i, acc)
                    # 准确率大于0.98时保存并退出
                    # if acc > 0.98 and n > 2:
                    #     saver.save(sess, './train_faces.model', global_step=n*num_batch+i)
                    #     print('accuracy > 0.98, success!')
                    #     sys.exit(0)
        saver.save(sess, './train_result/train_faces.model', global_step=n*num_batch+i)
        print('accuracy = %f' % acc)

def recognize_face():

    def is_my_face(image):
        res = sess.run(predict, feed_dict={x: [image/255.0], keep_prob_5:1.0, keep_prob_75: 1.0})
        if res[0] == 1:
            return True
        else:
            return False

    x = tf.placeholder(tf.float32, [None, 64, 64, 3])
    y_ = tf.placeholder(tf.float32, [None, 2])
    keep_prob_5 = tf.placeholder(tf.float32)
    keep_prob_75 = tf.placeholder(tf.float32)

    # 第一层
    W1 = weightVariable([3,3,3,32]) # 卷积核大小(3,3)， 输入通道(3)， 输出通道(32)
    b1 = biasVariable([32])
    # 卷积
    conv1 = tf.nn.relu(conv2d(x, W1) + b1)
    # 池化
    pool1 = maxPool(conv1)
    # 减少过拟合，随机让某些权重不更新
    drop1 = dropout(pool1, keep_prob_5)

    # 第二层
    W2 = weightVariable([3,3,32,64])
    b2 = biasVariable([64])
    conv2 = tf.nn.relu(conv2d(drop1, W2) + b2)
    pool2 = maxPool(conv2)
    drop2 = dropout(pool2, keep_prob_5)

    # 第三层
    W3 = weightVariable([3,3,64,64])
    b3 = biasVariable([64])
    conv3 = tf.nn.relu(conv2d(drop2, W3) + b3)
    pool3 = maxPool(conv3)
    drop3 = dropout(pool3, keep_prob_5)

    # 全连接层
    Wf = weightVariable([8*16*32, 512])
    bf = biasVariable([512])
    drop3_flat = tf.reshape(drop3, [-1, 8*16*32])
    dense = tf.nn.relu(tf.matmul(drop3_flat, Wf) + bf)
    dropf = dropout(dense, keep_prob_75)

    # 输出层
    Wout = weightVariable([512,2])
    bout = weightVariable([2])
    output = tf.add(tf.matmul(dropf, Wout), bout)

    predict = tf.argmax(output, 1)

    saver = tf.train.Saver()
    sess = tf.Session()
    saver.restore(sess, tf.train.latest_checkpoint('./train_result'))

    haar = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    cam = cv2.VideoCapture(0)

    while True:
        _, img = cam.read()
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = haar.detectMultiScale(gray_img, 1.3, 5)
        if not len(faces):
            print('Can`t get face.')
            cv2.imshow('Video', img)
            key = cv2.waitKey(30) & 0xff
            if key == 27:
                sys.exit(0)
        else:
            for f_x, f_y, f_w, f_h in faces:
                face = img[f_y:f_y+f_h, f_x:f_x+f_w]
                # 调整图片的尺寸
                face = cv2.resize(face, (64,64))
                print('Is this my face? %s' % is_my_face(face))
                cv2.rectangle(img, (f_x,f_y),(f_x+f_w,f_y+f_h), (255,0,0),3)
                cv2.imshow('Video',img)
                key = cv2.waitKey(30) & 0xff
                if key == 27:
                    sys.exit(0)

    sess.close()