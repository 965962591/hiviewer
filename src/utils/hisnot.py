# -*- coding: utf-8 -*-
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


"""全局函数"""

def toRectF(rect):
    """将输入的整数矩形转换为浮点矩形"""
    return QRectF(
        rect.x(),
        rect.y(),
        rect.width(),
        rect.height()
    )


def toRect(rectF):
    """将输入的浮点矩形转换为整数矩形"""
    return QRect(
        int(rectF.x()),
        int(rectF.y()), 
        int(rectF.width()),  
        int(rectF.height()) 
    )


def normalizeRect(rect):
    """确保矩形的坐标和尺寸是有效的，避免出现负值的情况"""
    x = rect.x()
    y = rect.y()
    w = max(rect.width(), 0)
    h = max(rect.height(), 0)
    if w < 0:
        x += w
    if h < 0:
        y += h
    return QRectF(x, y, w, h)


"""截图类"""
class WScreenshot(QWidget):
    @classmethod
    def run(cls):
        cls.win = cls()
        cls.win.getScreen()
        cls.win.show()
      
    def __init__(self,):
        super(WScreenshot, self).__init__()
        self.saveFormat = 'png'
        self.picQuality = 100
        self.clipboard = QApplication.clipboard() #实例化剪贴板
        self.setWindowTitle(u'截图窗体')
        self.showFullScreen()  # 全屏显示，设置窗口在顶部，去除窗口边框和标题栏
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

    def captureMouseScreen(self):
        cursor_pos = QCursor.pos()  # 获取鼠标当前位置
        screen = QApplication.primaryScreen()  # 获取主屏幕
        for s in QApplication.screens():  # 遍历所有屏幕
            if s.geometry().contains(cursor_pos):  # 检查鼠标是否在当前屏幕内
                screen = s  # 找到鼠标所在的屏幕
                break
        return screen.grabWindow(0)  # 抓取鼠标所在屏幕的图像

    def getScreen(self):
        
        # 抓取鼠标所在屏幕
        self.screen = self.captureMouseScreen()
        # 抓取主屏幕信息并保存,考虑到用户使用多显示器的情况，暂时移除该逻辑
        # self.screen = QApplication.primaryScreen().grabWindow(QApplication.desktop().winId())

        # 获取屏幕尺寸，屏幕浮点矩形 self.screenRect
        self.screenSize = self.screen.rect().size()
        self.screenRect = toRectF(self.screen.rect())
        # -点 四个角的坐标
        self.screenTopLeft = self.screenRect.topLeft()           # A
        self.screenBottomLeft = self.screenRect.bottomLeft()     # B
        self.screenTopRight = self.screenRect.topRight()         # D
        self.screenBottomRight = self.screenRect.bottomRight()   # C
        # -上下左右限  四个边界的坐标
        self.screenLeft = self.screenRect.left()                # 0.0 
        self.screenRight = self.screenRect.right()              # 屏幕w
        self.screenTop = self.screenRect.top()                  # 0.0
        self.screenBottom = self.screenRect.bottom()            # 屏幕h

        # A:start(x,y)        D:(x+w,y)
        #     -----------------
        #     |               |
        #     |               |
        #     -----------------
        # B:(x,y+h)           C:end(x+w,y+h)

        # 设置 self.screen 为窗口背景
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(self.screen))
        self.setPalette(palette)

        # 调节器层
        self.adjustment_original = QPixmap(self.screenSize)  # 初始调节器
        self.adjustment_original.fill(QColor(0, 0, 0, 64))
        self.adjustment = QPixmap()  # 调节器
        # self.adjustment = self.adjustment_original.copy()  # 调节器

        # 画布层
        self.canvas_original = QPixmap(self.screenSize)  # 初始画布
        self.canvas_original.fill(Qt.transparent)
        self.canvas_saved = self.canvas_original.copy()  # 保存已经画好的图案
        self.canvas = QPixmap()  # 画布

        # self.canvas = self.canvas_original.copy()  # 画布
        # self.canvas_saved = self.canvas.copy()
        # 输出
        self.output = QPixmap()

        # 当前功能状态
        self.isMasking = False
        self.hasMask = False
        self.isMoving = False
        self.isAdjusting = False
        self.isDrawing = False
        self.hasPattern = False
        self.mousePos = ''
        self.isShifting = False

        # 蒙版 和 蒙版信息
        self.maskRect = QRectF()
        self.maskRect_backup = QRectF()

        # 以下 16 个变量随self.maskRect变化而变化
        self.maskTopLeft = QPointF()
        self.maskBottomLeft = QPointF()
        self.maskTopRight = QPointF()
        self.maskBottomRight = QPointF()
        self.maskTopMid = QPointF()
        self.maskBottomMid = QPointF()
        self.maskLeftMid = QPointF()
        self.maskRightMid = QPointF()

        self.rectTopLeft = QRectF()
        self.rectBottomLeft = QRectF()
        self.rectTopRight = QRectF()
        self.rectBottomRight = QRectF()
        self.rectTop = QRectF()
        self.rectBottom = QRectF()
        self.rectLeft = QRectF()
        self.rectRight = QRectF()

        self.adjustmentLineWidth = 2
        self.adjustmentWhiteDotRadius = 6
        self.adjustmentBlueDotRadius = 4
        self.blue = QColor(30, 120, 255)
        self.setCursor(Qt.CrossCursor)  # 设置鼠标样式 十字

        self.setMouseTracking(True)     # 启用鼠标追踪功能

        # 鼠标事件点
        self.start = QPointF()
        self.end = QPointF()

        # 设置一个基础大小鼠标移动进行截图
        # self.test()

    def test(self):
        self.hasMask = True
        self.isMasking = True
        self.maskRect = QRectF(100, 100, 600, 800)
        self.updateMaskInfo()
        self.update()

    def toMask(self):
        """根据鼠标操作，更新蒙版矩形(maskRect)"""
        # 获取矩形,（鼠标按下的起始点，鼠标释放的结束点）
        rect = QRectF(self.start, self.end)

        if self.isShifting:
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
            absW, absH = abs(w), abs(h)
            wIsLonger = absW > absH
            end = QPointF(
                x + (absW if w > 0 else -absW),
                y + (absH if h > 0 else -absH)
            ) if wIsLonger else QPointF(
                x + (absH if w > 0 else -absH),
                y + (absW if h > 0 else -absW)
            )
            rect = QRectF(self.start, end)

        self.maskRect = QRectF(
            rect.x() + min(rect.width(), 0),
            rect.y() + min(rect.height(), 0),
            abs(rect.width()),
            abs(rect.height())
        )

        if self.isShifting:
            self.fixCollision()

        self.updateMaskInfo()
        self.update()

    # 修复碰撞。针对 isShifting 的情况
    def fixCollision(self):
        vector = self.end - self.start
        vX = vector.x()
        vY = vector.y()
        resStart = self.maskRect.topLeft()
        resEnd = self.maskRect.bottomRight()
        mLeft = self.maskRect.left()
        mRight = self.maskRect.right()
        mTop = self.maskRect.top()
        mBottom = self.maskRect.bottom()
        # w < h
        if self.maskRect.left() <= self.screenLeft:
            newW = mRight - self.screenLeft
            if vY > 0:
                resStart = QPointF(self.screenLeft, mTop)
                resEnd = resStart + QPointF(newW, newW)
            else:
                resStart = resEnd + QPointF(-newW, -newW)
        elif self.maskRect.right() >= self.screenRight:
            newW = self.screenRight - mLeft
            if vY > 0:
                resEnd = resStart + QPointF(newW, newW)
            else:
                resEnd = QPointF(self.screenRight, mBottom)
                resStart = resEnd + QPointF(-newW, -newW)
        # w > h
        elif self.maskRect.top() <= self.screenTop:
            newW = mBottom - self.screenTop
            if vX > 0:
                resStart = QPointF(mLeft, self.screenTop)
                resEnd = resStart + QPointF(newW, newW)
            else:
                resStart = resEnd + QPointF(-newW, -newW)
        elif self.maskRect.bottom() >= self.screenBottom:
            newW = self.screenBottom - mTop
            if vX > 0:
                resEnd = resStart + QPointF(newW, newW)
            else:
                resEnd = QPointF(mRight, self.screenBottom)
                resStart = resEnd + QPointF(-newW, -newW)
        self.maskRect = QRectF(resStart, resEnd)


    def toAdjust(self):
        """调整蒙版大小"""
        mRect = self.maskRect_backup
        mStart, mEnd = mRect.topLeft(), mRect.bottomRight()
        resStart, resEnd = mStart, mEnd

        if not self.isShifting:
            adjustments = {
                'TL': lambda: self.end,
                'BL': lambda: QPointF(self.end.x(), mStart.y()),  # 起始点都会改变
                'TR': lambda: QPointF(mStart.x(), self.end.y()),  # 起始点都会改变
                'BR': lambda: self.end,
                'T': lambda: QPointF(mStart.x(), self.end.y()),  
                'B': lambda: QPointF(mEnd.x(), self.end.y()),
                'L': lambda: QPointF(self.end.x(), mStart.y()),  
                'R': lambda: QPointF(self.end.x(), mEnd.y())
            }
            # 选择需要改变的起始点坐标
            if self.mousePos in ['T', 'L', 'TL']:
                resStart = adjustments.get(self.mousePos, lambda: mStart)()
            elif self.mousePos in ['B', 'R', 'BR']:
                resEnd = adjustments.get(self.mousePos, lambda: mEnd)()
            elif self.mousePos in ['BL',]:
                resStart = adjustments.get(self.mousePos, lambda: mStart)()
                resEnd = QPointF(mEnd.x(), self.end.y())
            elif self.mousePos in ['TR',]:
                resStart = adjustments.get(self.mousePos, lambda: mStart)()
                resEnd = QPointF(self.end.x(), mEnd.y(), )
                
        else:
            newW, newH = mEnd.x() - self.end.x(), mEnd.y() - self.end.y()
            adjustments = {
                'T': lambda: (QPointF(mStart.x(), self.end.y()), newW),
                'B': lambda: (resStart, newW),
                'L': lambda: (QPointF(self.end.x(), mStart.y()), newW),
                'R': lambda: (resStart, newW),
                'TL': lambda: (resEnd + QPointF(-max(newW, newH), -max(newW, newH)), None),
                'BR': lambda: (resStart, None),
                'TR': lambda: (mRect.bottomLeft(), None),
                'BL': lambda: (mRect.topRight(), None)
            }
            resStart, newW = adjustments.get(self.mousePos, lambda: (resStart, None))()

        self.maskRect = normalizeRect(QRectF(resStart, resEnd))
        self.fixCollision()
        self.updateMaskInfo()
        self.update()

    def toMove(self):
        """移动蒙版事件"""
        mStart = self.maskRect_backup.topLeft()
        mStartX = mStart.x()
        mStartY = mStart.y()
        mEnd = self.maskRect_backup.bottomRight()
        mEndX = mEnd.x()
        mEndY = mEnd.y()
        mWidth = self.maskRect_backup.width()
        mHeight = self.maskRect_backup.height()
        mWHPoint = QPointF(int(mWidth), int(mHeight))  # 确保参数为整数
        vector = self.end - self.start
        vX = vector.x()
        vY = vector.y()

        resStart = QPointF((mStartX + vX), (mStartY + vY))  # 转换为整数
        resEnd = QPointF((mEndX + vX), (mEndY + vY))  # 转换为整数

        if resStart.x() <= self.screenLeft and resStart.y() <= self.screenTop:
            resStart = self.screenTopLeft
            resEnd = resStart + mWHPoint
        elif resEnd.x() >= self.screenRight and resEnd.y() >= self.screenBottom:
            resEnd = self.screenBottomRight
            resStart = resEnd - mWHPoint
        elif resStart.x() <= self.screenLeft and resEnd.y() >= self.screenBottom:
            resStart = QPointF((self.screenLeft), (self.screenBottom - mHeight))  # 确保为整数
            resEnd = resStart + mWHPoint
        elif resEnd.x() >= self.screenRight and resStart.y() <= self.screenTop:
            resStart = QPointF((self.screenRight - mWidth), (self.screenTop))  # 确保为整数
            resEnd = resStart + mWHPoint
        elif resStart.x() <= self.screenLeft:
            resStart = QPointF((self.screenLeft), (mStartY + vY))  # 确保为整数
            resEnd = resStart + mWHPoint
        elif resStart.y() <= self.screenTop:
            resStart = QPointF((mStartX + vX), (self.screenTop))  # 确保为整数
            resEnd = resStart + mWHPoint
        elif resEnd.x() >= self.screenRight:
            resEnd = QPointF((self.screenRight), (mEndY + vY))  # 确保为整数
            resStart = resEnd - mWHPoint
        elif resEnd.y() >= self.screenBottom:
            resEnd = QPointF((mEndX + vX), (self.screenBottom))  # 确保为整数
            resStart = resEnd - mWHPoint

        self.maskRect = normalizeRect(QRectF(resStart, resEnd))
        self.updateMaskInfo()
        self.update()

    def mousePressEvent(self, QMouseEvent):
        """鼠标按压事件"""
        if QMouseEvent.button() == Qt.LeftButton:
            self.start = QMouseEvent.pos()
            self.end = self.start
            if self.hasMask:
                self.maskRect_backup = self.maskRect
                if self.mousePos == 'mask':
                    self.isMoving = True
                else:
                    self.isAdjusting = True
            else:
                self.isMasking = True

        if QMouseEvent.button() == Qt.RightButton:
            if self.isMasking or self.hasMask:
                self.isMasking = False
                self.hasMask = False
                self.maskRect = QRectF(0, 0, 0, 0)
                self.updateMaskInfo()
                self.update()
            else:
                self.close()

    def mouseReleaseEvent(self, QMouseEvent):
        """鼠标释放事件"""
        if QMouseEvent.button() == Qt.LeftButton:
            self.isMasking = False
            self.isMoving = False
            self.isAdjusting = False
            self.isDrawing = False

    def mouseDoubleClickEvent(self, QMouseEvent):
        """鼠标双击事件"""
        if QMouseEvent.button() == Qt.LeftButton:
            if self.mousePos == 'mask':
                self.save()
                self.close()

    def mouseMoveEvent(self, QMouseEvent):
        """鼠标移动事件"""
        pos = QMouseEvent.pos()
        self.end = pos

        if self.isMasking:
            self.hasMask = True
            self.toMask()
        elif self.isMoving:
            self.toMove()
        elif self.isAdjusting:
            self.toAdjust()

        # 设置鼠标样式
        if self.isDrawing:
            pass
        else:
            if self.hasMask:
                if self.isMoving:
                    self.setCursor(Qt.SizeAllCursor)
                if self.isAdjusting:
                    pass
                else:
                    self.setMouseShape(pos)
            else:
                self.mousePos = ''
                self.setCursor(Qt.CrossCursor)  # 设置鼠标样式 十字

        self.update()  # 只在所有处理完成后调用一次更新


    def setMouseShape(self, pos):
        """设置鼠标形状，根据鼠标当前位置设置鼠标指针的形状"""
        # 根据蒙版外八个区域+蒙版区域设置鼠标形状
        cursor_map = {
            'TL': (self.rectTopLeft, Qt.SizeFDiagCursor),
            'BL': (self.rectBottomLeft, Qt.SizeBDiagCursor),
            'BR': (self.rectBottomRight, Qt.SizeFDiagCursor),
            'TR': (self.rectTopRight, Qt.SizeBDiagCursor),
            'L': (self.rectLeft, Qt.SizeHorCursor),
            'T': (self.rectTop, Qt.SizeVerCursor),
            'B': (self.rectBottom, Qt.SizeVerCursor),
            'R': (self.rectRight, Qt.SizeHorCursor),
            'mask': (self.maskRect, Qt.SizeAllCursor)
        }

        for pos_key, (rect, cursor) in cursor_map.items():
            if rect.contains(pos):
                self.setCursor(cursor)
                self.mousePos = pos_key
                return  # 找到匹配后直接返回

        # 如果没有匹配的区域，可以设置默认光标
        self.setCursor(Qt.ArrowCursor)  # 默认光标

    def updateMaskInfo(self):
        """更新蒙版矩形的信息和坐标点"""
        # (maskTopLeft)1      (maskTopMid)5   (maskTopRight)2
        #     .---------------.-------------------.
        #     |                                   |
        #     .(maskLeftMid)7        8(maskRightMid).
        #     |                                   |
        #     .-----------------.-----------------.
        # (maskBottomLeft)3  (maskBottomMid)6  (maskBottomRight)4
        # 8个蒙版点（截图区域矩形框的八个点，四个边角点+四个中点）
        self.maskTopLeft = self.maskRect.topLeft()
        self.maskBottomLeft = self.maskRect.bottomLeft()
        self.maskTopRight = self.maskRect.topRight()
        self.maskBottomRight = self.maskRect.bottomRight()
        # 计算中点
        calculateMidpoint = lambda p1, p2: (p1 + p2) / 2
        self.maskTopMid = calculateMidpoint(self.maskTopLeft, self.maskTopRight)
        self.maskBottomMid = calculateMidpoint(self.maskBottomLeft, self.maskBottomRight)
        self.maskLeftMid = calculateMidpoint(self.maskTopLeft, self.maskBottomLeft)
        self.maskRightMid = calculateMidpoint(self.maskTopRight, self.maskBottomRight)

        # 设置除蒙版区外的 8 个矩形区域
        self.rectTopLeft = QRectF(self.screenTopLeft, self.maskTopLeft)                                   # 左上斜角矩形区域
        self.rectBottomLeft = QRectF(self.screenBottomLeft, self.maskBottomLeft)                          # 左下斜角矩形区域
        self.rectTopRight = QRectF(self.screenTopRight, self.maskTopRight)                                # 右上斜角矩形区域
        self.rectBottomRight = QRectF(self.screenBottomRight, self.maskBottomRight)                       # 右下斜角矩形区域
        self.rectTop = QRectF(QPointF(self.maskRect.left(), self.screenTop), self.maskTopRight)           # 蒙版矩形正上矩形区域
        self.rectBottom = QRectF(self.maskBottomLeft, QPointF(self.maskRect.right(), self.screenBottom))  # 蒙版矩形正下矩形区域
        self.rectLeft = QRectF(QPointF(self.screenLeft, self.maskRect.top()), self.maskBottomLeft)        # 蒙版矩形左边矩形区域
        self.rectRight = QRectF(self.maskTopRight, QPointF(self.screenRight, self.maskRect.bottom()))     # 蒙版矩形右边矩形区域
    

    def paintEvent(self, QPaintEvent):
        """重写绘图事件，根据当前状态绘制画布或调节器"""
        painter = QPainter()

        # 开始在 画布层 上绘画。如果正在绘画，绘制图案, 否则不绘制
        if self.isDrawing:
            if self.hasPattern:
                self.canvas = self.canvas_saved.copy()
            else:
                self.canvas = self.canvas_original.copy()
            painter.begin(self.canvas)
            self.paintCanvas(painter)
            painter.end()
            # 把 画布层 绘画到窗口上
            painter.begin(self)
            painter.drawPixmap(self.screenRect, self.canvas)
            painter.end()

        # 开始在 空白调节器层 上绘画。如果有蒙版，绘制调节器形状, 否则不绘制
        else:
            self.adjustment = self.adjustment_original.copy()
            painter.begin(self.adjustment)
            self.paintAdjustment(painter)
            painter.end()
            # 把 调节器层 绘画到窗口上
            painter.begin(self)
            painter.drawPixmap(toRect(self.screenRect), self.adjustment)
            painter.end()

    def paintAdjustment(self, painter):
        """绘制蒙版的调节器形状和尺寸信息"""
        if self.hasMask:
            painter.setRenderHint(QPainter.Antialiasing, True)  # 反走样
            painter.setPen(Qt.NoPen)
            # 在蒙版区绘制屏幕背景
            painter.setBrush(QBrush(self.screen))
            painter.drawRect(self.maskRect)
            # 绘制线框
            lineWidth = self.adjustmentLineWidth
            painter.setBrush(self.blue)
            painter.drawRect(
                QRectF(
                    self.maskTopLeft + QPointF(-lineWidth, -lineWidth),
                    self.maskTopRight + QPointF(lineWidth, 0))
            )
            painter.drawRect(
                QRectF(
                    self.maskBottomLeft + QPointF(-lineWidth, 0),
                    self.maskBottomRight + QPointF(lineWidth, lineWidth)
                )
            )
            painter.drawRect(
                QRectF(
                    self.maskTopLeft + QPointF(-lineWidth, -lineWidth),
                    self.maskBottomLeft + QPointF(0, lineWidth)
                )
            )
            painter.drawRect(
                QRectF(
                    self.maskTopRight + QPointF(0, -lineWidth),
                    self.maskBottomRight + QPointF(lineWidth, lineWidth)
                )
            )
            if self.maskRect.width() > 150 and self.maskRect.height() > 150:
                # 绘制点
                points = [
                    self.maskTopLeft, self.maskTopRight, self.maskBottomLeft, self.maskBottomRight,
                    self.maskLeftMid, self.maskRightMid, self.maskTopMid, self.maskBottomMid
                ]
                # -白点
                whiteDotRadiusPoint = QPointF(self.adjustmentWhiteDotRadius, self.adjustmentWhiteDotRadius)
                painter.setBrush(Qt.white)
                for point in points:
                    painter.drawEllipse(QRectF(point - whiteDotRadiusPoint, point + whiteDotRadiusPoint))
                # -蓝点
                blueDotRadius = QPointF(self.adjustmentBlueDotRadius, self.adjustmentBlueDotRadius)
                painter.setBrush(self.blue)
                for point in points:
                    painter.drawEllipse(QRectF(point - blueDotRadius, point + blueDotRadius))

            # 绘制尺寸
            maskSize = (abs(int(self.maskRect.width())), abs(int(self.maskRect.height())))
            painter.setFont(QFont('Monaco', 7, QFont.Bold))
            painter.setPen(Qt.transparent)  # 透明获得字体Rect
            textRect = painter.drawText(
                QRectF(self.maskTopLeft.x() + 10, self.maskTopLeft.y() - 25, 100, 20),
                Qt.AlignLeft | Qt.AlignVCenter,
                '{} x {}'.format(*maskSize)
            )
            painter.setBrush(QColor(0, 0, 0, 128))  # 黑底
            padding = 5
            painter.drawRect(
                QRectF(
                    textRect.x() - padding,
                    textRect.y() - padding * 0.4,
                    textRect.width() + padding * 2,
                    textRect.height() + padding * 0.4
                )
            )
            painter.setPen(Qt.white)
            painter.drawText(
                textRect,
                Qt.AlignLeft | Qt.AlignVCenter,
                '{} x {}'.format(*maskSize)
            )
            painter.setPen(Qt.NoPen)

    def paintCanvas(self, painter):
        """绘制画布（目前未实现具体功能"""
        pass

    def keyPressEvent(self, event):
        '''全局快捷键'''
          #QtCore.Qt.Key_+按键名（Escape=Esc）-->事件值
        if event.key() == Qt.Key_Escape:
            self.win.close()

    def keyPressEvent(self, QKeyEvent):
        """处理键盘按压事件"""
        # ESC退出窗口
        if QKeyEvent.key() == Qt.Key_Escape:
            self.close()
        # 回车键(大键盘、小键盘回车),保存截图并退出窗口
        if QKeyEvent.key() == Qt.Key_Return or QKeyEvent.key() == Qt.Key_Enter:  
            if self.hasMask:
                self.save()
            self.close()
        # 按住shift键 切换状态 为 True
        if QKeyEvent.modifiers() & Qt.ShiftModifier:
            self.isShifting = True

    def keyReleaseEvent(self, QKeyEvent):
        # 释放shift键 切换状态 为 False
        if QKeyEvent.key() == Qt.Key_Shift:
            self.isShifting = False

    def save(self):
        """保存截图为png图片并粘贴到系统剪贴板中"""
        self.output = self.screen.copy()
        
        if self.hasPattern:
            painter = QPainter(self.output)
            painter.drawPixmap(self.canvas)
        
        self.output = self.output.copy(toRect(self.maskRect))
        self.clipboard.setPixmap(self.output)  # 写入剪贴板
        
        # 确保保存路径存在
        save_path = "ocr.png"  # 可以考虑使用文件对话框让用户选择路径
        try:
            self.output.save(save_path, self.saveFormat, self.picQuality)
        except Exception as e:
            print(f"保存文件时出错: {e}")  # 添加异常处理


# 在你的主程序中
if __name__ == "__main__":
    app = QApplication(sys.argv)  # 创建应用程序
    WScreenshot.run()  # 调用类方法运行截图功能
    sys.exit(app.exec_())  # 进入应用程序主循环