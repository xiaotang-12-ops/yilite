<template>
<div class="worker-manual-viewer">
    <!-- 历史版本只读提示条 -->
    <div v-if="isReadOnlyMode" class="history-notice-bar">
      <div class="history-notice-content">
        <el-icon><Clock /></el-icon>
        <span>正在查看历史版本 <strong>{{ historyVersion }}</strong>（只读模式）</span>
      </div>
      <div class="history-notice-actions">
        <el-button size="small" @click="exitHistoryPreview">
          退出
        </el-button>
        <el-button size="small" @click="router.push(`/manual/${props.taskId}`)">
          修改当前版本
        </el-button>
        <el-button size="small" type="primary" @click="router.push(`/version-history/${props.taskId}`)">
          版本历史
        </el-button>
      </div>
    </div>

    <!-- 草稿模式提示条 -->
    <div v-if="isAdmin && isDraftMode && !isReadOnlyMode" class="draft-notice-bar">
      <div class="draft-notice-content">
        <el-icon><Warning /></el-icon>
        <span>草稿模式 - 您有未发布的修改</span>
      </div>
      <div class="draft-notice-actions">
        <el-button size="small" :loading="discardingDraft" @click="handleDiscardDraft">
          丢弃修改
        </el-button>
        <el-button type="success" size="small" @click="openPublishDialog">
          立即发布
        </el-button>
      </div>
    </div>

    <!-- 顶部进度条 -->
    <div class="top-bar">
      <div class="product-info">
        <h1>{{ productName }}</h1>
        <el-tag v-if="!isMobile" type="info" size="large">装配说明书</el-tag>
      </div>

      <div class="progress-section">
        <div class="progress-info">
          <span class="current-step">步骤 {{ currentStepIndex + 1 }}</span>
          <span class="total-steps">/ {{ totalSteps }}</span>
          <span class="step-title">{{ currentStepData?.title }}</span>
        </div>
        <el-progress
          :percentage="progressPercentage"
          :stroke-width="10"
          :color="progressColor"
        />
      </div>

      <div class="top-actions">
        <!-- 导航组 -->
        <div class="action-group nav-group">
          <el-button :disabled="currentStepIndex === 0" @click="previousStep">
            <el-icon><ArrowLeft /></el-icon>
            上一步
          </el-button>
          <span class="step-indicator">{{ currentStepIndex + 1 }} / {{ totalSteps }}</span>
          <el-button type="primary" :disabled="currentStepIndex === totalSteps - 1" @click="nextStep">
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>

        <!-- 管理员登录/管理按钮（只读模式下隐藏） -->
        <template v-if="!isReadOnlyMode && !isMobile">
          <!-- 未登录状态 -->
          <div v-if="!isAdmin" class="action-group">
            <el-button @click="showLoginDialog = true">
              <el-icon><Lock /></el-icon>
              管理员登录
            </el-button>
          </div>

          <!-- 已登录状态 -->
          <template v-else>
            <!-- 分隔线 -->
            <div class="action-divider"></div>

            <!-- 功能组 -->
            <div class="action-group function-group">
              <el-dropdown trigger="click" @command="handleEditCommand">
                <el-button>
                  <el-icon><Edit /></el-icon>
                  编辑 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="editContent">
                      <el-icon><Edit /></el-icon> 编辑内容
                    </el-dropdown-item>
                    <el-dropdown-item command="insertStep">
                      <el-icon><Plus /></el-icon> 插入步骤
                    </el-dropdown-item>
                    <el-dropdown-item command="deleteStep" divided>
                      <el-icon><Delete /></el-icon> 删除当前步骤
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <el-dropdown trigger="click" @command="handleVersionCommand">
                <el-button>
                  <el-icon><Upload /></el-icon>
                  版本 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="publish">
                      <el-icon><Upload /></el-icon> 发布新版本
                    </el-dropdown-item>
                    <el-dropdown-item command="history">
                      <el-icon><Document /></el-icon> 历史版本
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <!-- 分隔线 -->
            <div class="action-divider"></div>

            <!-- 状态组 -->
            <div class="action-group status-group">
              <span class="admin-badge">
                <el-icon><User /></el-icon>
                管理员
              </span>
              <el-button @click="logout">退出</el-button>
            </div>
          </template>
        </template>
      </div>
    </div>

    <template v-if="manualData">
    <div class="mobile-action-bar" v-if="isMobile">
      <el-button type="primary" plain @click="showDrawingsDrawer = true">
        <el-icon><Picture /></el-icon>
        图纸
      </el-button>
      <el-button type="primary" plain @click="showDetailsDrawer = true">
        <el-icon><Document /></el-icon>
        步骤/参考
      </el-button>
      <el-button
        :type="isAutoPlaying ? 'danger' : 'success'"
        plain
        @click="toggleAutoPlay"
      >
        <el-icon><VideoPlay v-if="!isAutoPlaying" /><VideoPause v-else /></el-icon>
        {{ isAutoPlaying ? '停止播放' : '自动播放' }}
      </el-button>
    </div>

    <!-- 主工作区 -->
    <div class="main-workspace">
      <!-- 左侧：图纸参考（全屏显示） -->
      <div class="left-sidebar" v-if="!isMobile">
      <div class="drawing-section-full">
        <div class="section-title">
          📐 图纸参考
          <span v-if="drawingImages.length > 1" class="page-indicator">
            共{{ drawingImages.length }}张
          </span>
        </div>
        <el-scrollbar class="drawings-container">
          <div class="drawings-list">
            <div
              v-for="(drawingUrl, index) in drawingImages"
              :key="index"
              class="drawing-item"
              :class="{ 'zoomed': zoomedDrawingIndex === index }"
              @click="toggleDrawingZoom(index)"
              @touchstart="handleDrawingTouchStart(index, $event)"
              @touchmove="handleDrawingTouchMove(index, $event)"
              @touchend="handleDrawingTouchEnd"
              @touchcancel="handleDrawingTouchEnd"
            >
              <div class="drawing-zoom-bar" v-if="isMobile" @click.stop>
                <el-button size="small" @click.stop="setDrawingScale(index, -0.1)">缩小</el-button>
                <span class="scale-text">{{ Math.round(getDrawingScale(index) * 100) }}%</span>
                <el-button size="small" @click.stop="setDrawingScale(index, 0.1)">放大</el-button>
                <el-button size="small" type="info" @click.stop="resetDrawingScale(index)">重置</el-button>
              </div>
              <img
                :src="drawingUrl"
                :alt="`工程图纸 ${index + 1}`"
                class="drawing-image"
                :style="{
                  transform: `scale(${getDrawingScale(index)})`,
                  transformOrigin: 'top center'
                }"
                @dragstart.prevent
              />
            </div>
            <div v-if="drawingImages.length === 0" class="drawing-placeholder">
              <el-icon :size="64" color="#ccc"><Picture /></el-icon>
              <p>暂无图纸</p>
            </div>
            </div>
          </el-scrollbar>
        </div>
      </div>

      <!-- 中间：3D模型 -->
      <div class="center-viewer">
        <div class="model-container" ref="modelContainer">
          <!-- Three.js 渲染区域 -->
        </div>

        <!-- 零件状态选择弹窗 - 仅管理员可见 -->
        <div
          v-if="showStatusPopup && isAdmin && selectedMesh"
          class="part-status-popup"
          :style="{
            left: statusPopupPosition.x + 'px',
            top: statusPopupPosition.y + 'px'
          }"
        >
          <div class="popup-header">
            <div class="part-info">
              <span class="part-name">{{ getPartDisplayName(selectedMesh) }}</span>
              <span class="part-nauo">NAUO: {{ getPartNauoName(selectedMesh) }}</span>
            </div>
            <el-button
              :icon="Close"
              circle
              size="small"
              @click="closeStatusPopup"
            />
          </div>
          <div class="popup-content">
            <el-button
              :type="getPartStatus(selectedMesh) === 'not_installed' ? 'info' : 'default'"
              @click="setPartStatus('not_installed')"
              size="small"
            >
              <span class="status-dot gray"></span>
              未装
            </el-button>
            <el-button
              :type="getPartStatus(selectedMesh) === 'installing' ? 'warning' : 'default'"
              @click="setPartStatus('installing')"
              size="small"
            >
              <span class="status-dot yellow"></span>
              正在装
            </el-button>
            <el-button
              :type="getPartStatus(selectedMesh) === 'installed' ? 'primary' : 'default'"
              @click="setPartStatus('installed')"
              size="small"
            >
              <span class="status-dot blue"></span>
              已装
            </el-button>
          </div>
          <div class="popup-footer">
            <el-button
              type="danger"
              size="small"
              @click="deletePart"
            >
              <el-icon><Delete /></el-icon>
              删除零件
            </el-button>
          </div>
        </div>

        <!-- 3D控制 -->
        <div class="model-controls">
          <div class="controls-row">
            <el-button-group :size="isMobile ? 'small' : 'default'">
              <el-button :icon="Refresh" @click="resetCamera">重置视角</el-button>
              <el-button
                :icon="View"
                :type="isExploded ? 'primary' : ''"
                @click="toggleExplode"
              >
                {{ isExploded ? '收起' : '爆炸' }}视图
              </el-button>
              <el-button
                :icon="Grid"
                :type="isWireframe ? 'primary' : ''"
                @click="toggleWireframe"
              >
                线框模式
              </el-button>
            </el-button-group>

            <!-- 爆炸比例滑块（放在按钮组同一行） -->
            <div v-if="isExploded && !isMobile" class="explode-slider-inline">
              <el-slider
                v-model="explodeScale"
                :min="0"
                :max="50"
                :step="1"
                :style="{ width: '180px' }"
              />
              <span class="slider-value">{{ explodeScale }}%</span>
            </div>

            <!-- 已删除零件下拉菜单（放在按钮组同一行） -->
            <el-dropdown v-if="deletedParts.size > 0 && isAdmin && !isMobile" trigger="click" @command="restorePart">
              <el-button type="warning" plain size="default">
                <el-icon><Delete /></el-icon>
                已删除 ({{ deletedParts.size }})
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="meshKey in deletedParts"
                    :key="meshKey"
                    :command="meshKey"
                  >
                    <span class="deleted-part-name">{{ getDeletedPartDisplayName(meshKey) }}</span>
                    <el-tag size="small" type="success">恢复</el-tag>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <!-- 移动端：爆炸滑块单独一行 -->
          <div v-if="isExploded && isMobile" class="explode-slider">
            <span class="slider-label">爆炸程度:</span>
            <el-slider
              v-model="explodeScale"
              :min="0"
              :max="50"
              :step="1"
              :style="{ width: '100%', margin: '0 8px' }"
            />
            <span class="slider-value">{{ explodeScale }}%</span>
          </div>

          <!-- 移动端：已删除零件单独一行 -->
          <div v-if="deletedParts.size > 0 && isAdmin && isMobile" class="deleted-parts-dropdown">
            <el-dropdown trigger="click" @command="restorePart">
              <el-button type="warning" plain size="small">
                <el-icon><Delete /></el-icon>
                已删除零件 ({{ deletedParts.size }})
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="meshKey in deletedParts"
                    :key="meshKey"
                    :command="meshKey"
                  >
                    <span class="deleted-part-name">{{ getDeletedPartDisplayName(meshKey) }}</span>
                    <el-tag size="small" type="success">恢复</el-tag>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- 右侧：当前步骤详情 -->
      <div class="right-sidebar" v-if="!isMobile">
        <el-scrollbar height="100%">

          <!-- 当前步骤 -->
          <div class="step-detail-card" v-if="currentStepData">
            <div class="step-header">
              <div class="step-badge">{{ currentStepIndex + 1 }}</div>
              <h2>{{ currentStepData.title }}</h2>
            </div>

            <div class="step-content">
              <!-- 描述 -->
              <div class="description-section">
                <p class="description-text">{{ currentStepData.description || currentStepData.operation }}</p>
              </div>

              <!-- 操作步骤 -->
              <div class="operations-section" v-if="currentStepData.operation_steps">
                <h3>📝 操作步骤</h3>
                <ol class="operation-list">
                  <li v-for="(op, index) in currentStepData.operation_steps" :key="index">
                    {{ op }}
                  </li>
                </ol>
              </div>

              <!-- 所需工具 -->
              <div class="tools-section" v-if="currentStepData.tools_required && currentStepData.tools_required.length">
                <h3>🔧 所需工具</h3>
                <div class="tools-tags">
                  <el-tag
                    v-for="tool in currentStepData.tools_required"
                    :key="tool"
                    type="info"
                    size="large"
                    effect="plain"
                  >
                    {{ tool }}
                  </el-tag>
                </div>
              </div>

              <!-- 关键点 -->
              <div class="keypoints-section" v-if="currentStepData.key_points && currentStepData.key_points.length">
                <h3>💡 关键点</h3>
                <ul class="keypoints-list">
                  <li v-for="(point, index) in currentStepData.key_points" :key="index">
                    {{ point }}
                  </li>
                </ul>
              </div>

              <!-- ✅ 移除：安全警告已在下方"安全"标签页中统一显示 -->

              <!-- 质检要求 -->
              <div class="operations-section" v-if="currentStepData.quality_check">
                <h3>✅ 质检要求</h3>
                <p>{{ currentStepData.quality_check }}</p>
              </div>

              <!-- 预计时间（隐藏展示，保留字段供后续使用） -->
              <div class="time-section" v-if="false">
                <el-icon><Clock /></el-icon>
                <span>预计时间: {{ currentStepData.estimated_time_minutes }} 分钟</span>
              </div>
            </div>
          </div>

          <!-- 快速参考标签页 -->
          <div class="quick-reference-tabs">
            <el-tabs v-model="activeTab" type="border-card">
              <el-tab-pane label="焊接" name="welding">
                <div class="tab-content-scroll">


                  <div
                    v-for="(req, index) in currentStepWeldingRequirements"
                    :key="index"
                    class="ref-item"
                  >
                    <div class="ref-header">
                      <strong>步骤{{ req.step_number }} - {{ req.component }}</strong>
                      <el-tag type="warning" size="small" v-if="req.welding_info?.required">
                        需要焊接
                      </el-tag>
                    </div>
                    <p v-if="req.welding_info?.welding_position">📍 {{ req.welding_info.welding_position }}</p>
                    <el-text type="info" size="small" v-if="req.welding_info">
                      {{ req.welding_info.welding_type || req.welding_info.welding_method }} - {{ req.welding_info.weld_size }}
                    </el-text>
                  </div>
                  <el-empty v-if="!currentStepWeldingRequirements.length" description="当前步骤无焊接要求" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="质检" name="quality">
                <div class="tab-content-scroll">
                  <div v-if="currentStepQualityCheck && currentStepQualityCheck.quality_check" class="ref-item">
                    <div class="ref-header">
                      <strong>步骤{{ currentStepQualityCheck.step_number }} - {{ currentStepQualityCheck.component }}</strong>
                    </div>
                    <p>{{ currentStepQualityCheck.quality_check }}</p>
                  </div>
                  <el-empty v-else description="当前步骤无质检要求" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="安全" name="safety">
                <div class="tab-content-scroll">
                  <el-alert
                    v-for="(warning, index) in currentStepSafetyWarnings"
                    :key="index"
                    :title="`步骤${warning.step_number} - ${warning.component}`"
                    type="warning"
                    :description="warning.warning"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 8px"
                  />
                  <el-empty v-if="!currentStepSafetyWarnings.length" description="当前步骤无安全警告" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="FAQ" name="faq">
                <div class="tab-content-scroll">
                  <div
                    v-for="(faq, index) in (manualData.safety_and_faq?.faq_items || manualData.faq_items || []).slice(0, 2)"
                    :key="index"
                    class="ref-item"
                  >
                    <div class="ref-header">
                      <strong>Q: {{ faq.question }}</strong>
                    </div>
                    <p>A: {{ faq.answer?.substring(0, 80) }}...</p>
                  </div>
                  <el-empty v-if="!(manualData.safety_and_faq?.faq_items || manualData.faq_items || []).length" description="暂无常见问题" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-scrollbar>
      </div>
    </div>

    <el-drawer
      v-if="isMobile"
      v-model="showDrawingsDrawer"
      title="图纸参考"
      size="90%"
      direction="ltr"
    >
      <div class="mobile-drawer-body">
        <div class="drawing-section-full">
          <div class="section-title">
            📐 图纸参考
            <span v-if="drawingImages.length > 1" class="page-indicator">
              共{{ drawingImages.length }}张
            </span>
          </div>
          <el-scrollbar class="drawings-container">
          <div class="drawings-list">
            <div
              v-for="(drawingUrl, index) in drawingImages"
              :key="index"
              class="drawing-item"
              :class="{ 'zoomed': zoomedDrawingIndex === index }"
              @click="toggleDrawingZoom(index)"
              @touchstart="handleDrawingTouchStart(index, $event)"
              @touchmove="handleDrawingTouchMove(index, $event)"
              @touchend="handleDrawingTouchEnd"
              @touchcancel="handleDrawingTouchEnd"
            >
              <div class="drawing-zoom-bar" v-if="isMobile" @click.stop>
                <el-button size="small" @click.stop="setDrawingScale(index, -0.1)">缩小</el-button>
                <span class="scale-text">{{ Math.round(getDrawingScale(index) * 100) }}%</span>
                <el-button size="small" @click.stop="setDrawingScale(index, 0.1)">放大</el-button>
                <el-button size="small" type="info" @click.stop="resetDrawingScale(index)">重置</el-button>
              </div>
              <img
                :src="drawingUrl"
                :alt="`工程图纸 ${index + 1}`"
                class="drawing-image"
                :style="{
                  transform: `scale(${getDrawingScale(index)})`,
                  transformOrigin: 'top center'
                }"
                @dragstart.prevent
              />
            </div>
              <div v-if="drawingImages.length === 0" class="drawing-placeholder">
                <el-icon :size="64" color="#ccc"><Picture /></el-icon>
                <p>暂无图纸</p>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </div>
    </el-drawer>

    <el-drawer
      v-if="isMobile"
      v-model="showDetailsDrawer"
      title="步骤与参考"
      size="90%"
      direction="rtl"
    >
      <div class="mobile-drawer-body">
        <el-scrollbar height="100%">
          <div class="step-detail-card" v-if="currentStepData">
            <div class="step-header">
              <div class="step-badge">{{ currentStepIndex + 1 }}</div>
              <h2>{{ currentStepData.title }}</h2>
            </div>

            <div class="step-content">
              <div class="description-section">
                <p class="description-text">{{ currentStepData.description || currentStepData.operation }}</p>
              </div>

              <div class="operations-section" v-if="currentStepData.operation_steps">
                <h3>📝 操作步骤</h3>
                <ol class="operation-list">
                  <li v-for="(op, index) in currentStepData.operation_steps" :key="index">
                    {{ op }}
                  </li>
                </ol>
              </div>

              <div class="tools-section" v-if="currentStepData.tools_required && currentStepData.tools_required.length">
                <h3>🔧 所需工具</h3>
                <div class="tools-tags">
                  <el-tag
                    v-for="tool in currentStepData.tools_required"
                    :key="tool"
                    type="info"
                    size="large"
                    effect="plain"
                  >
                    {{ tool }}
                  </el-tag>
                </div>
              </div>

              <div class="keypoints-section" v-if="currentStepData.key_points && currentStepData.key_points.length">
                <h3>💡 关键点</h3>
                <ul class="keypoints-list">
                  <li v-for="(point, index) in currentStepData.key_points" :key="index">
                    {{ point }}
                  </li>
                </ul>
              </div>

              <div class="operations-section" v-if="currentStepData.quality_check">
                <h3>✅ 质检要求</h3>
                <p>{{ currentStepData.quality_check }}</p>
              </div>
            </div>
          </div>

          <div class="quick-reference-tabs">
            <el-tabs v-model="activeTab" type="border-card">
              <el-tab-pane label="焊接" name="welding">
                <div class="tab-content-scroll">


                  <div
                    v-for="(req, index) in currentStepWeldingRequirements"
                    :key="index"
                    class="ref-item"
                  >
                    <div class="ref-header">
                      <strong>步骤{{ req.step_number }} - {{ req.component }}</strong>
                      <el-tag type="warning" size="small" v-if="req.welding_info?.required">
                        需要焊接
                      </el-tag>
                    </div>
                    <p v-if="req.welding_info?.welding_position">📍 {{ req.welding_info.welding_position }}</p>
                    <el-text type="info" size="small" v-if="req.welding_info">
                      {{ req.welding_info.welding_type || req.welding_info.welding_method }} - {{ req.welding_info.weld_size }}
                    </el-text>
                  </div>
                  <el-empty v-if="!currentStepWeldingRequirements.length" description="当前步骤无焊接要求" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="质检" name="quality">
                <div class="tab-content-scroll">
                  <div v-if="currentStepQualityCheck && currentStepQualityCheck.quality_check" class="ref-item">
                    <div class="ref-header">
                      <strong>步骤{{ currentStepQualityCheck.step_number }} - {{ currentStepQualityCheck.component }}</strong>
                    </div>
                    <p>{{ currentStepQualityCheck.quality_check }}</p>
                  </div>
                  <el-empty v-else description="当前步骤无质检要求" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="安全" name="safety">
                <div class="tab-content-scroll">
                  <el-alert
                    v-for="(warning, index) in currentStepSafetyWarnings"
                    :key="index"
                    :title="`步骤${warning.step_number} - ${warning.component}`"
                    type="warning"
                    :description="warning.warning"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 8px"
                  />
                  <el-empty v-if="!currentStepSafetyWarnings.length" description="当前步骤无安全警告" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="FAQ" name="faq">
                <div class="tab-content-scroll">
                  <div
                    v-for="(faq, index) in (manualData.safety_and_faq?.faq_items || manualData.faq_items || []).slice(0, 2)"
                    :key="index"
                    class="ref-item"
                  >
                    <div class="ref-header">
                      <strong>Q: {{ faq.question }}</strong>
                    </div>
                    <p>A: {{ faq.answer?.substring(0, 80) }}...</p>
                  </div>
                  <el-empty v-if="!(manualData.safety_and_faq?.faq_items || manualData.faq_items || []).length" description="暂无常见问题" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-scrollbar>
      </div>
    </el-drawer>
    </template>

    <template v-else>
      <div class="loading-screen">
        <el-icon class="is-loading" :size="64">
          <Loading />
        </el-icon>
        <p>加载装配说明书中...</p>
      </div>
    </template>

    <!-- 管理员登录Dialog -->
    <el-dialog
      v-model="showLoginDialog"
      title="管理员登录"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="loginForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLoginDialog = false">取消</el-button>
        <el-button type="primary" @click="handleLogin">登录</el-button>
      </template>
    </el-dialog>

    <!-- 插入步骤Dialog -->
    <el-dialog
      v-model="showInsertDialog"
      title="插入新步骤"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form label-width="100px">
        <el-form-item label="插入位置">
          <el-select v-model="insertAfterStepId" placeholder="选择插入位置" style="width: 100%;">
            <el-option :label="'在开头插入'" :value="null" />
            <el-option
              v-for="step in allSteps"
              :key="step.step_id"
              :label="`在步骤${step.step_number}「${step.action || '未命名'}」之后`"
              :value="step.step_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="步骤标题">
          <el-input v-model="insertAction" placeholder="例如：安装新零件" />
        </el-form-item>
        <el-form-item label="步骤描述">
          <el-input v-model="insertDescription" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInsertDialog = false">取消</el-button>
        <el-button type="primary" :loading="inserting" @click="handleInsertStep">确认插入</el-button>
      </template>
    </el-dialog>

    <!-- 内容编辑Dialog -->
  <el-dialog
    v-model="showEditDialog"
    :title="`编辑步骤${currentStepData?.step_number} - ${currentStepData?.action}`"
    width="800px"
    :close-on-click-modal="false"
  >
    <!-- 当前步骤组件名称（统一入口，避免分散在焊接/安全表单里导致遗漏） -->
    <el-form label-width="100px" style="margin-bottom: 12px">
      <el-form-item label="组件名称">
        <el-input
          v-model="componentNameInput"
          placeholder="例如：固定座组件"
        />
        <el-text type="info" size="small" style="margin-left: 8px;">
          这里修改的名称会同步到当前步骤及所属组件
        </el-text>
      </el-form-item>
    </el-form>

    <el-tabs v-model="editActiveTab">
      <!-- 步骤描述 -->
      <el-tab-pane label="步骤描述" name="description">
        <div class="edit-section">
          <el-alert
            title="提示"
            type="info"
            :closable="false"
            style="margin-bottom: 12px"
          >
            编辑当前步骤的文字描述（同步到 description/operation 字段）
          </el-alert>
          <el-input
            v-model="editData.step_description"
            type="textarea"
            :rows="6"
            placeholder="请输入该步骤的描述"
          />
        </div>
      </el-tab-pane>

      <!-- 焊接注意事项 -->
      <el-tab-pane label="焊接注意事项" name="welding">
        <div class="edit-section">
          <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              当前步骤的焊接要求（步骤{{ currentStepData?.step_number }}）
            </el-alert>

            <el-button
              type="primary"
              size="small"
              @click="addWeldingRequirement"
              :disabled="editData.welding_requirements.length >= 1"
              style="margin-bottom: 12px"
            >
              <el-icon><Plus /></el-icon>
              添加焊接要求
            </el-button>
            <el-text v-if="editData.welding_requirements.length >= 1" type="info" size="small" style="margin-left: 8px;">
              每个步骤只能有一个焊接要求，如需修改请先删除现有要求
            </el-text>

            <div
              v-for="(req, index) in editData.welding_requirements"
              :key="index"
              class="welding-edit-card"
            >
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>焊接要求 #{{ index + 1 }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      @click="removeWeldingRequirement(index)"
                    >
                      删除
                    </el-button>
                  </div>
                </template>

                <el-form label-width="120px">
                  <el-form-item label="步骤号">
                    <el-input-number
                      v-model="req.step_number"
                      :min="1"
                      placeholder="步骤号"
                      disabled
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      步骤号由当前步骤自动确定
                    </el-text>
                  </el-form-item>

                  <el-form-item label="组件名称">
                    <el-input
                      v-model="componentNameInput"
                      placeholder="例如：固定座组件"
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      修改组件名称会同步更新到当前步骤
                    </el-text>
                  </el-form-item>

                  <el-divider content-position="left">焊接信息</el-divider>

                  <el-form-item label="是否需要焊接">
                    <el-switch v-model="req.welding_info.required" />
                  </el-form-item>

                  <el-form-item label="焊接类型">
                    <el-input
                      v-model="req.welding_info.welding_type"
                      placeholder="例如：角焊（定位焊）"
                    />
                  </el-form-item>

                  <el-form-item label="焊缝尺寸">
                    <el-input
                      v-model="req.welding_info.weld_size"
                      placeholder="例如：点焊，焊点长度约10mm"
                    />
                  </el-form-item>

                  <el-form-item label="焊接位置">
                    <el-input
                      v-model="req.welding_info.welding_position"
                      type="textarea"
                      :rows="2"
                      placeholder="例如：加强板（③）与卷圆板（①）的连接处"
                    />
                  </el-form-item>
                </el-form>
              </el-card>
            </div>

            <el-empty v-if="!editData.welding_requirements.length" description="暂无焊接要求" />
          </div>
        </el-tab-pane>

        <!-- 安全警告 -->
        <el-tab-pane label="安全警告" name="safety">
          <div class="edit-section">
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              当前步骤的安全警告（步骤{{ currentStepData?.step_number }}）
            </el-alert>

            <el-button
              type="primary"
              size="small"
              @click="addSafetyWarning"
              style="margin-bottom: 12px"
            >
              <el-icon><Plus /></el-icon>
              添加安全警告
            </el-button>

            <div
              v-for="(warning, index) in editData.safety_warnings"
              :key="index"
              class="safety-edit-card"
            >
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>安全警告 #{{ index + 1 }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      @click="removeSafetyWarning(index)"
                    >
                      删除
                    </el-button>
                  </div>
                </template>

                <el-form label-width="100px">
                  <el-form-item label="步骤号">
                    <el-input-number
                      v-model="warning.step_number"
                      :min="1"
                      placeholder="步骤号"
                      disabled
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      步骤号由当前步骤自动确定
                    </el-text>
                  </el-form-item>

                  <el-form-item label="组件名称">
                    <el-input
                      v-model="componentNameInput"
                      placeholder="例如：固定座组件"
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      修改组件名称会同步更新到当前步骤
                    </el-text>
                  </el-form-item>

                  <el-form-item label="警告内容">
                    <el-input
                      v-model="warning.warning"
                      type="textarea"
                      :rows="3"
                      placeholder="例如：卷圆板属于重物，必须使用行车或叉车进行吊运"
                    />
                  </el-form-item>
                </el-form>
              </el-card>
            </div>

            <el-empty v-if="!editData.safety_warnings.length" description="暂无安全警告" />
          </div>
        </el-tab-pane>

        <!-- 质检要求 -->
        <el-tab-pane label="质检要求" name="quality">
          <div class="edit-section">
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              当前步骤的质检要求（步骤{{ currentStepData?.step_number }}）
            </el-alert>

            <el-form label-width="100px">
              <el-form-item label="质检要求">
                <el-input
                  v-model="editData.quality_check"
                  type="textarea"
                  :rows="6"
                  placeholder="例如：检查焊点牢固性，确保无裂纹、气孔等缺陷"
                />
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- FAQ -->
        <el-tab-pane label="常见问题" name="faq">
          <div class="edit-section">
            <el-button
              type="primary"
              size="small"
              @click="addFaqItem"
              style="margin-bottom: 12px"
            >
              <el-icon><Plus /></el-icon>
              添加FAQ
            </el-button>
            <div
              v-for="(faq, index) in editData.faq_items"
              :key="index"
              class="edit-item"
            >
              <el-input
                v-model="faq.question"
                placeholder="问题"
                style="margin-bottom: 8px"
              />
              <el-input
                v-model="faq.answer"
                type="textarea"
                :rows="2"
                placeholder="答案"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeFaqItem(index)"
                style="margin-top: 8px"
              >
                删除
              </el-button>
            </div>
            <el-empty v-if="!editData.faq_items.length" description="暂无常见问题" />
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDraft" :loading="saving">💾 保存草稿</el-button>
      </template>
    </el-dialog>

    <!-- 发布 Dialog -->
    <el-dialog
      v-model="showPublishDialog"
      title="🚀 发布新版本"
      width="520px"
    >
      <el-form label-width="100px">
        <el-form-item label="当前版本">
          <el-tag type="info">{{ manualData?.version || '未发布' }}</el-tag>
        </el-form-item>
        <el-form-item label="即将发布">
          <el-tag type="success">{{ nextVersionPreview }}</el-tag>
        </el-form-item>
        <el-form-item label="版本说明" required>
          <el-input
            v-model="publishForm.changelog"
            type="textarea"
            :rows="4"
            placeholder="请填写本次发布的变更说明"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPublishDialog = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="confirmPublish">
          确认发布✅
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Loading, ArrowLeft, ArrowRight, ArrowDown, Picture, Box,
  Refresh, View, Grid, Clock, Lock, Edit, Plus, Upload, Document,
  Warning, Delete, Close, User, VideoPlay, VideoPause
} from '@element-plus/icons-vue'
import { useMediaQuery } from '@vueuse/core'
import axios from 'axios'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'

// ============ 辅助函数 ============



// ============ 类型定义 ============

// 焊接要求编辑类型
interface WeldingRequirementEdit {
  step_id: string
  step_number: number
  component: string
  welding_info: {
    required: boolean
    welding_type: string
    weld_size: string
    welding_position: string
  }
}

// 安全警告编辑类型
interface SafetyWarningEdit {
  step_number: number
  component: string
  warning: string
}

// ✅ 接收路由参数 taskId
const props = defineProps<{
  taskId: string
}>()

const isMobile = useMediaQuery('(max-width: 1024px)')
const showDrawingsDrawer = ref(false)
const showDetailsDrawer = ref(false)
let viewerInitAttempts = 0

const router = useRouter()
const route = useRoute()

// 历史版本只读模式（通过 ?version=v2 参数触发）
const historyVersion = computed(() => route.query.version as string | undefined)
const isReadOnlyMode = computed(() => !!historyVersion.value)

const manualData = ref<any>(null)
// ✅ 存储 step3_glb_inventory.json 的 node_to_geometry 数据（用于显示3D零件实际名称）
const glbNodeToGeometry = ref<{ node: string; geometry: string }[]>([])

const setManualDataValue = (data: any) => {
  manualData.value = data
  if (manualData.value && manualData.value._edit_version === undefined) {
    manualData.value._edit_version = 0
  }

  // ✅ 从 part_assembly_states 恢复零件状态到内存 Map
  restorePartAssemblyStates(data)
}

// 从 manualData.part_assembly_states 恢复零件装配状态
const restorePartAssemblyStates = (data: any) => {
  // 恢复零件装配状态
  if (!data?.part_assembly_states) {
    partAssemblyStates.value.clear()
  } else {
    const savedStates = data.part_assembly_states as Record<string, Record<string, AssemblyStatus>>
    partAssemblyStates.value.clear()

    for (const [stepId, stepStates] of Object.entries(savedStates)) {
      const stepMap = new Map<string, AssemblyStatus>()
      for (const [meshKey, status] of Object.entries(stepStates)) {
        stepMap.set(meshKey, status as AssemblyStatus)
      }
      partAssemblyStates.value.set(stepId, stepMap)
    }
    console.log(`✅ 恢复零件装配状态: ${partAssemblyStates.value.size} 个步骤`)
  }

  // 恢复已删除零件
  if (data?.deleted_parts && Array.isArray(data.deleted_parts)) {
    deletedParts.value = new Set(data.deleted_parts)
    console.log(`✅ 恢复已删除零件: ${deletedParts.value.size} 个`)
  } else {
    deletedParts.value.clear()
  }
}
const currentStepIndex = ref(0)
const activeTab = ref('welding')

// 自动播放相关
const isAutoPlaying = ref(false)
let autoPlayTimer: ReturnType<typeof setInterval> | null = null
const modelContainer = ref<HTMLElement | null>(null)

const nextVersionPreview = computed(() => {
  const raw = manualData.value?.version || 'v0'
  const numeric = parseInt(String(raw).replace(/[^0-9]/g, ''), 10)
  const next = Number.isNaN(numeric) ? 1 : numeric + 1
  return `v${next}`
})

// 管理员相关
const isAdmin = ref(false)
const isDraftMode = ref(false)  // 是否处于草稿模式
const discardingDraft = ref(false)  // 正在丢弃草稿
const showLoginDialog = ref(false)
const showEditDialog = ref(false)
const showPublishDialog = ref(false)
const publishForm = ref({ changelog: '' })
const publishing = ref(false)
const editActiveTab = ref('welding')
const saving = ref(false)
const componentNameInput = ref('')
const showInsertDialog = ref(false)
const insertAfterStepId = ref<string | null>(null)
const insertAction = ref('')
const insertDescription = ref('')
const inserting = ref(false)
const deletingStep = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

// 编辑数据（使用新的类型定义）
const editData = ref({
  welding_requirements: [] as WeldingRequirementEdit[],
  safety_warnings: [] as SafetyWarningEdit[],
  quality_check: '' as string,
  step_description: '' as string,
  faq_items: [] as Array<{ question: string; answer: string }>
})

// 🔧 记录编辑前的原始步骤号（用于保存时精确删除）
const originalStepNumber = ref<number>(0)

// Three.js 相关
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let model: THREE.Group | null = null
let gridHelper: THREE.GridHelper | null = null

// 保存每个mesh的原始位置、材质和爆炸方向
let meshOriginalPositions: Map<string, THREE.Vector3> = new Map()
let meshOriginalMaterials: Map<string, THREE.Material> = new Map()
let meshExplodeDirections: Map<string, THREE.Vector3> = new Map()

// ✅ 使用世界坐标系存储，以避免层级导致的局部位置重合问题
let meshWorldOriginalPositions: Map<string, THREE.Vector3> = new Map()
let meshWorldExplodeDirections: Map<string, THREE.Vector3> = new Map()


const isExploded = ref(true) // 初始爆炸，未装配件分散
const isWireframe = ref(false)
const explodeScale = ref(25) // 爆炸比例（0-50，默认25）

// ============ 零件交互选中功能（管理员专用） ============
// 装配状态类型定义
type AssemblyStatus = 'not_installed' | 'installing' | 'installed'

// Raycaster 相关
let raycaster: THREE.Raycaster | null = null
const mouse = new THREE.Vector2()

// 悬浮和选中状态
const hoveredMesh = ref<THREE.Mesh | null>(null)
const selectedMesh = ref<THREE.Mesh | null>(null)

// 边框线条组
let hoverOutlineGroup: THREE.Group | null = null

// 状态弹窗
const statusPopupPosition = ref({ x: 0, y: 0 })
const showStatusPopup = ref(false)

// 装配状态存储 (stepId -> (meshKey -> status))，按步骤独立存储
// 解决步骤切换时颜色状态混乱的问题
const partAssemblyStates = ref<Map<string, Map<string, AssemblyStatus>>>(new Map())

// 已删除零件存储（全局，所有步骤都不显示）
const deletedParts = ref<Set<string>>(new Set())

// 自动保存防抖计时器
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

// 区分点击和拖拽
let mouseDownPosition = { x: 0, y: 0 }
let mouseDownTime = 0

// 图纸缩放相关
const zoomedDrawingIndex = ref<number | null>(null)

// 获取当前步骤的图纸列表
const drawingImages = computed(() => {
  if (!currentStepData.value) {
    console.log('⚠️ 当前步骤数据为空')
    return []
  }

  const stepData = currentStepData.value

  // 1. 优先从当前步骤中获取图纸
  const stepDrawings = stepData.drawings ||
                       stepData.pdf_images ||
                       stepData.technical_drawings ||
                       stepData.drawing_images ||
                       []

  if (Array.isArray(stepDrawings) && stepDrawings.length > 0) {
    console.log(`✅ 步骤${currentStepIndex.value + 1}有${stepDrawings.length}张图纸`)
    return stepDrawings
  }

  // 2. 如果步骤中没有图纸，尝试从全局获取
  if (manualData.value) {
    // 从3d_resources中获取
    const resources3d = manualData.value['3d_resources']
    if (resources3d?.pdf_images && Array.isArray(resources3d.pdf_images)) {
      console.log('✅ 从3d_resources.pdf_images找到', resources3d.pdf_images.length, '张图纸（全局）')
      return resources3d.pdf_images
    }

    // 从product_assembly中获取
    const productAssembly = manualData.value.product_assembly
    if (productAssembly?.pdf_images && Array.isArray(productAssembly.pdf_images)) {
      console.log('✅ 从product_assembly.pdf_images找到', productAssembly.pdf_images.length, '张图纸（全局）')
      return productAssembly.pdf_images
    }
  }

  // 3. ⚠️ 临时方案：如果都没有，使用默认路径
  // TODO: 等后端在每个步骤中添加图纸字段后，这段代码会自动失效
  console.warn(`⚠️ 步骤${currentStepIndex.value + 1}未找到图纸数据，使用默认路径（临时方案）`)
  const taskId = props.taskId
  return [
    `/api/manual/${taskId}/pdf_images/page_001.png`,
    `/api/manual/${taskId}/pdf_images/page_002.png`
  ]
})

const productName = computed(() => {
  if (!manualData.value) return '加载中...'
  return manualData.value?.product_overview?.product_name || '装配说明书'
})

// ✅ 构建完整的步骤列表：组件装配 + 产品装配（按 display_order 排序，并动态计算 step_number）
const allSteps = computed(() => {
  const collected: any[] = []
  let fallbackOrder = 1000

  // 1. 添加组件装配步骤
  const componentAssembly = manualData.value?.component_assembly || []
  console.log('🔍 [allSteps] 组件装配数量:', componentAssembly.length)

  for (const component of componentAssembly) {
    const componentSteps = component.steps || []
    console.log(`🔍 [allSteps] 组件 \"${component.component_name}\" 的步骤数量:`, componentSteps.length)

    for (const step of componentSteps) {
      const order = typeof step.display_order === 'number' ? step.display_order : fallbackOrder
      fallbackOrder += 1000
      const stepData = {
        ...step,
        display_order: order,
        chapter_type: 'component_assembly',
        component_code: component.component_code,
        component_name: component.component_name,
        glb_file: component.glb_file
      }
      collected.push(stepData)
    }
  }

  // 2. 产品装配步骤
  const productSteps = manualData.value?.product_assembly?.steps || []
  console.log('🔍 [allSteps] 产品装配步骤数量:', productSteps.length)

  for (const step of productSteps) {
    const order = typeof step.display_order === 'number' ? step.display_order : fallbackOrder
    fallbackOrder += 1000
    const stepData = {
      ...step,
      display_order: order,
      chapter_type: 'product_assembly',
      glb_file: 'product_total.glb'
    }
    collected.push(stepData)
  }

  const sorted = collected.sort((a, b) => {
    const aOrder = typeof a.display_order === 'number' ? a.display_order : 0
    const bOrder = typeof b.display_order === 'number' ? b.display_order : 0
    return aOrder - bOrder
  })

  const withStepNumber = sorted.map((step, idx) => ({
    ...step,
    step_number: idx + 1
  }))

  console.log('🔍 [allSteps] 排序后步骤数量:', withStepNumber.length)
  console.log('🔍 [allSteps] 前5步:', withStepNumber.slice(0, 5).map(s => ({
    step_number: s.step_number,
    display_order: s.display_order,
    action: s.action,
    chapter_type: s.chapter_type
  })))

  return withStepNumber
})

const stepNumberMap = computed(() => {
  const map = new Map<string, number>()
  allSteps.value.forEach((step, idx) => map.set(step.step_id, idx + 1))
  return map
})

const totalSteps = computed(() => {
  return allSteps.value.length
})

const currentStepData = computed(() => {
  const stepData = allSteps.value[currentStepIndex.value]

  // 调试：查看步骤数据中是否有图纸字段
  if (stepData) {
    console.log(`📋 步骤${currentStepIndex.value + 1}的数据:`, stepData)
    console.log(`🎨 步骤${currentStepIndex.value + 1}的字段:`, Object.keys(stepData))
  }

  return stepData
})

const currentStepParts = computed(() => {
  // ✅ 兼容两种数据结构：parts_used 或 fasteners
  return currentStepData.value?.parts_used || currentStepData.value?.fasteners || []
})

// 提取步骤中的 node_name 列表（兼容数组/单值），覆盖 parts_used/components/fasteners/3d_highlight
const getStepNodeNames = (step: any): string[] => {
  const names: string[] = []
  if (!step) return names
  const collect = (items: any) => {
    if (!items) return
    for (const part of items) {
      if (!part) continue
      const node = (part as any).node_name
      if (Array.isArray(node)) {
        names.push(...node)
      } else if (node) {
        names.push(node)
      }
    }
  }
  collect(step.parts_used)
  collect(step.components)
  collect(step.fasteners)
  if (Array.isArray(step['3d_highlight'])) {
    names.push(...step['3d_highlight'])
  }
  return names.filter(Boolean)
}

const currentStepNodeNames = computed(() => getStepNodeNames(currentStepData.value))

const previousStepNodeNames = computed(() => {
  const names: string[] = []
  for (let i = 0; i < currentStepIndex.value; i++) {
    const step = allSteps.value[i]
    names.push(...getStepNodeNames(step))
  }
  return names
})

const assembledNodeNames = computed(() => {
  const names: string[] = []
  for (let i = 0; i <= currentStepIndex.value; i++) {
    const step = allSteps.value[i]
    names.push(...getStepNodeNames(step))
  }
  return names
})

// ✅ node_name 到零件名称的映射（用于显示实际零件名称而非NAUO序号）
// 优先使用 step3_glb_inventory.json 的 geometry 字段（3D零件实际名称）
const nodeNameToPartName = computed(() => {
  const mapping = new Map<string, string>()

  // ✅ 优先使用 glbNodeToGeometry（来自 step3_glb_inventory.json）
  // 这是最准确的3D零件名称，如 "GB╱T 5782-2016[六角头螺栓M20×90]_M20×90"
  for (const item of glbNodeToGeometry.value) {
    if (item.node && item.geometry) {
      mapping.set(item.node, item.geometry)
    }
  }

  // 如果 glbNodeToGeometry 没有数据，回退到 BOM 映射表
  if (mapping.size === 0) {
    const resources3d = (manualData.value as any)?.['3d_resources']
    const componentMappings = resources3d?.component_level_mappings

    if (componentMappings) {
      for (const [, componentData] of Object.entries(componentMappings)) {
        const bomMappingTable = (componentData as any)?.bom_mapping_table
        if (Array.isArray(bomMappingTable)) {
          for (const item of bomMappingTable) {
            const name = item.name || item.bom_name || ''
            const nodeNames = item.node_names || []
            if (name && Array.isArray(nodeNames)) {
              for (const nodeName of nodeNames) {
                if (nodeName && !mapping.has(nodeName)) {
                  mapping.set(nodeName, name)
                }
              }
            }
          }
        }
      }
    }
  }

  return mapping
})

// ✅ 根据当前步骤的零件自动生成3D高亮mesh列表
const currentStepHighlightMeshes = computed(() => {
  const highlightMeshes: string[] = []
  const allParts: any[] = []

  // ✅ 收集所有需要高亮的零件（主要组件 + 紧固件 + parts_used）
  // 1. 产品装配步骤：components + fasteners
  if (currentStepData.value?.components) {
    // 过滤掉空值
    allParts.push(...currentStepData.value.components.filter((c: any) => c))
  }
  if (currentStepData.value?.fasteners) {
    // 过滤掉空值
    allParts.push(...currentStepData.value.fasteners.filter((f: any) => f))
  }

  // 2. 组件装配步骤：parts_used
  if (currentStepData.value?.parts_used) {
    // 过滤掉空值
    allParts.push(...currentStepData.value.parts_used.filter((p: any) => p))
  }

  // ✅ 3. 从描述中提取BOM序号（如"4、5号矩形管"中的4和5，或"⑨号加强筋"中的9）
  const description: string = (currentStepData.value as any)?.description || ''
  if (description) {
    // 圆圈数字到普通数字的映射
    const circleToNumber: { [key: string]: string } = {
      '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
      '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '10'
    }

    // 匹配模式：普通数字+号 或 圆圈数字+号
    // 例如："4号"、"4、5号"、"⑨号"、"⑥号"
    const bomSeqPattern = /([①②③④⑤⑥⑦⑧⑨⑩\d]+)[、，号]/g
    const matches = description.matchAll(bomSeqPattern)
    const extractedSeqs = new Set<string>()

    for (const match of matches) {
      let seq = match[1]
      // 如果是圆圈数字，转换为普通数字
      if (circleToNumber[seq]) {
        seq = circleToNumber[seq]
      }
      extractedSeqs.add(seq)
    }

    if (extractedSeqs.size > 0) {
      console.log(`  📝 从描述中提取到BOM序号:`, Array.from(extractedSeqs))

      // 从BOM映射表中查找这些序号对应的node_name
      const componentCode = (currentStepData.value as any)?.component_code
      console.log(`  🔑 当前组件代码:`, componentCode)

      const resources3d = (manualData.value as any)?.['3d_resources']
      console.log(`  📦 3D资源:`, resources3d ? '存在' : '不存在')

      const componentMappings = resources3d?.component_level_mappings
      console.log(`  📦 组件级别映射:`, componentMappings ? Object.keys(componentMappings) : '不存在')

      const bomMappingTable = componentMappings?.[componentCode]?.bom_mapping_table
      console.log(`  📋 BOM映射表:`, bomMappingTable ? `存在(${bomMappingTable.length}项)` : '不存在')

      if (bomMappingTable) {
        console.log(`  📋 BOM映射表中的所有seq:`, bomMappingTable.map((item: any) => `${item.seq}(${typeof item.seq})`))

        extractedSeqs.forEach(seq => {
          console.log(`  🔍 查找seq="${seq}"(${typeof seq})`)
          const bomItem = bomMappingTable.find((item: any) => item.seq === seq)

          if (bomItem) {
            console.log(`  ✅ 找到BOM项:`, bomItem)
            if (bomItem.node_names && bomItem.node_names.length > 0) {
              allParts.push({
                bom_code: bomItem.code,
                bom_seq: seq,
                node_name: bomItem.node_names,
                from_description: true
              })
              console.log(`  📝 描述中的${seq}号 → ${bomItem.code} → ${bomItem.node_names.length}个node`)
            } else {
              console.warn(`  ⚠️  ${seq}号BOM项没有node_names字段或为空数组`)
            }
          } else {
            console.warn(`  ❌ 未找到seq="${seq}"的BOM项`)
          }
        })
      } else {
        console.warn(`  ⚠️  无法获取BOM映射表，componentCode=${componentCode}`)
      }
    }
  }

  // ✅ 优先使用零件中的node_name字段（直接使用GLB中的node名称）
  allParts.forEach((part: any) => {
    if (part.node_name) {
      // node_name可能是数组或单个值
      if (Array.isArray(part.node_name)) {
        highlightMeshes.push(...part.node_name)
        const source = part.from_description ? '(从描述提取)' : '(直接指定)'
        console.log(`  ✅ ${part.bom_code || part.code} → ${part.node_name.length} 个node ${source}:`, part.node_name)
      } else {
        highlightMeshes.push(part.node_name)
        const source = part.from_description ? '(从描述提取)' : '(直接指定)'
        console.log(`  ✅ ${part.bom_code || part.code} → 1 个node ${source}:`, part.node_name)
      }
    } else if (part.mesh_id) {
      // 兼容旧数据：如果有mesh_id，也支持
      if (Array.isArray(part.mesh_id)) {
        highlightMeshes.push(...part.mesh_id)
        console.log(`  ⚠️  ${part.bom_code || part.code} → ${part.mesh_id.length} 个mesh (旧格式):`, part.mesh_id)
      } else {
        highlightMeshes.push(part.mesh_id)
        console.log(`  ⚠️  ${part.bom_code || part.code} → 1 个mesh (旧格式):`, part.mesh_id)
      }
    } else {
      console.warn(`  ❌ ${part.bom_code || part.code} 没有node_name或mesh_id`)
    }
  })

  console.log(`🎯 步骤${currentStepIndex.value + 1}需要高亮的零件:`, allParts.map(p => p.bom_code || p.code))
  console.log(`🎯 步骤${currentStepIndex.value + 1}需要高亮的mesh (${highlightMeshes.length}个):`, highlightMeshes)
  return highlightMeshes
})

// 图纸点击放大功能
const toggleDrawingZoom = (index: number) => {
  if (zoomedDrawingIndex.value === index) {
    zoomedDrawingIndex.value = null
  } else {
    zoomedDrawingIndex.value = index
  }
}

// 图纸缩放控制（移动端默认缩小）
const drawingScales = ref<Record<number, number>>({})
const getDrawingScale = (index: number) => {
  const defaultScale = isMobile.value ? 0.6 : 1
  return drawingScales.value[index] ?? defaultScale
}
const setDrawingScale = (index: number, delta: number) => {
  const next = Math.min(2, Math.max(0.3, getDrawingScale(index) + delta))
  drawingScales.value = { ...drawingScales.value, [index]: next }
}

// 触摸缩放（双指捏合）
const pinchState = reactive({
  isPinching: false,
  startDistance: 0,
  startScale: 1,
  targetIndex: -1
})

const getTouchDistance = (event: TouchEvent) => {
  const [t1, t2] = [event.touches[0], event.touches[1]]
  const dx = t1.clientX - t2.clientX
  const dy = t1.clientY - t2.clientY
  return Math.hypot(dx, dy)
}

const handleDrawingTouchStart = (index: number, event: TouchEvent) => {
  if (event.touches.length === 2) {
    pinchState.isPinching = true
    pinchState.startDistance = getTouchDistance(event)
    pinchState.startScale = getDrawingScale(index)
    pinchState.targetIndex = index
  }
}

const handleDrawingTouchMove = (index: number, event: TouchEvent) => {
  if (!pinchState.isPinching || pinchState.targetIndex !== index) return
  if (event.touches.length !== 2) return
  event.preventDefault()
  const currentDistance = getTouchDistance(event)
  const ratio = currentDistance / (pinchState.startDistance || 1)
  const nextScale = Math.min(2, Math.max(0.3, pinchState.startScale * ratio))
  drawingScales.value = { ...drawingScales.value, [index]: nextScale }
}

const handleDrawingTouchEnd = () => {
  pinchState.isPinching = false
  pinchState.targetIndex = -1
}
const resetDrawingScale = (index: number) => {
  drawingScales.value = { ...drawingScales.value, [index]: isMobile.value ? 0.6 : 1 }
}

// ✅ 过滤当前步骤的焊接信息（只从步骤内嵌字段读取）
const currentStepWeldingRequirements = computed(() => {
  const currentStep = currentStepData.value
  if (!currentStep?.welding?.required) return []

  // 将步骤内嵌的 welding 字段转换为数组格式（保持UI兼容性）
  return [{
    step_id: currentStep.step_id,
    step_number: currentStep.step_number,
    component: currentStep.component_name || '',
    welding_info: currentStep.welding
  }]
})

// ✅ 过滤当前步骤的安全警告（只从步骤内嵌字段读取）
const currentStepSafetyWarnings = computed(() => {
  const currentStep = currentStepData.value
  if (!currentStep) return []

  // 从步骤内嵌字段读取（字符串数组），转换为对象数组（用于显示）
  const warnings = currentStep.safety_warnings || []
  return warnings.map((warning: string) => ({
    step_number: currentStep.step_number,
    component: currentStep.component_name || '',
    warning: warning
  }))
})

// ✅ 从所有步骤中提取质检要求
const qualityCheckpoints = computed(() => {
  const checkpoints: any[] = []

  // 从组件装配步骤中提取
  const componentAssembly = manualData.value?.component_assembly || []
  for (const component of componentAssembly) {
    const steps = component.steps || []
    for (const step of steps) {
      if (step.quality_check) {
        const mappedNumber = stepNumberMap.value.get(step.step_id) || step.step_number
        checkpoints.push({
          step_number: mappedNumber,
          component: component.component_name,
          quality_check: step.quality_check
        })
      }
    }
  }

  // 从产品装配步骤中提取
  const productSteps = manualData.value?.product_assembly?.steps || []
  for (const step of productSteps) {
    if (step.quality_check) {
      const mappedNumber = stepNumberMap.value.get(step.step_id) || step.step_number
      checkpoints.push({
        step_number: mappedNumber,
        component: '产品总装',
        quality_check: step.quality_check
      })
    }
  }

  return checkpoints
})

// ✅ 当前步骤的质检要求
const currentStepQualityCheck = computed(() => {
  const currentStep = currentStepData.value
  if (!currentStep) return null

  return {
    step_number: currentStep.step_number,
    component: currentStep.component_name || '产品总装',
    quality_check: currentStep.quality_check || ''
  }
})

const progressPercentage = computed(() => {
  if (totalSteps.value === 0) return 0
  return ((currentStepIndex.value + 1) / totalSteps.value) * 100
})

const progressColor = computed(() => {
  const percentage = progressPercentage.value
  if (percentage < 30) return '#409eff'
  if (percentage < 70) return '#e6a23c'
  return '#67c23a'
})

// ✅ 初始化3D查看器和模型
const init3DViewerAndModel = async () => {
  console.log('🚀 开始初始化3D查看器和模型...')
  await new Promise(resolve => setTimeout(resolve, 100)) // 等待DOM更新
  console.log('⏰ DOM更新等待完成')
  init3DViewer()
  console.log('⏰ 3D查看器初始化完成，开始加载模型...')
  await load3DModel()
  console.log('🎉 3D查看器和模型初始化全部完成')

  // ✅ 延迟后重新调整渲染器尺寸，确保容器已完全渲染
  await new Promise(resolve => setTimeout(resolve, 200))
  if (modelContainer.value && renderer && camera) {
    const width = modelContainer.value.clientWidth
    const height = modelContainer.value.clientHeight
    console.log('🔄 重新调整渲染器尺寸:', { width, height })
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }
}

// ============ 管理员功能 ============

// 管理员登录
const handleLogin = () => {
  const { username, password } = loginForm.value

  // 硬编码验证
  if (username === 'admin' && password === 'admin123') {
    isAdmin.value = true
    sessionStorage.setItem('isAdmin', 'true')
    showLoginDialog.value = false
    ElMessage.success('登录成功！')
    loginForm.value = { username: '', password: '' }
  } else {
    ElMessage.error('用户名或密码错误')
  }
}

// 退出登录
const logout = () => {
  isAdmin.value = false
  sessionStorage.removeItem('isAdmin')
  ElMessage.success('已退出管理员模式')
}

// 打开编辑Dialog时初始化数据（只加载当前步骤的数据）
// 🔧 修复：记住原始 step_id，用于保存时精确删除
watch(showEditDialog, (newVal) => {
  if (newVal && manualData.value && currentStepData.value) {
    const currentStep = currentStepData.value
    const currentStepId = currentStep.step_id
    const currentStepNumber = currentStep.step_number
    const currentComponentName = currentStep.component_name

    // 🔧 记住原始步骤号（兼容性）
    originalStepNumber.value = currentStepNumber
    componentNameInput.value = currentComponentName || ''

    // 从步骤内嵌字段加载焊接数据
    if (currentStep.welding && currentStep.welding.required) {
      editData.value.welding_requirements = [{
        step_id: currentStepId,
        step_number: currentStepNumber,
        component: currentComponentName || componentNameInput.value,
        welding_info: JSON.parse(JSON.stringify(currentStep.welding))
      }]
    } else {
      editData.value.welding_requirements = []
    }

    // 从步骤内嵌字段加载安全警告
    editData.value.safety_warnings = (currentStep.safety_warnings || []).map((warning: string) => ({
      step_number: currentStepNumber,
      component: currentComponentName || componentNameInput.value,
      warning: warning
    }))

    // 加载当前步骤的质检要求
    editData.value.quality_check = currentStep.quality_check || ''

    // FAQ是全局的，不按步骤过滤
    const safetyAndFaq = manualData.value.safety_and_faq || {}
    editData.value.faq_items = JSON.parse(JSON.stringify(safetyAndFaq.faq_items || []))
    editData.value.step_description = currentStep.description || currentStep.operation || ''

    console.log('📝 [编辑数据初始化完成]')
    console.log('  - 原始步骤号:', originalStepNumber.value)
    console.log('  - 当前组件名称:', currentComponentName)
    console.log('  - 当前步骤焊接要求数量:', editData.value.welding_requirements.length)
    console.log('  - 当前步骤安全警告数量:', editData.value.safety_warnings.length)
    console.log('  - 当前步骤质检要求:', editData.value.quality_check)
  }
})

// 添加/删除焊接要求
const addWeldingRequirement = () => {
  const currentStep = currentStepData.value
  const stepId = currentStep?.step_id || ''
  const stepNumber = currentStep?.step_number || 1
  const componentName = currentStep?.component_name || ''

  console.log('➕ [添加焊接要求]', { stepId, stepNumber, componentName })

  editData.value.welding_requirements.push({
    step_id: stepId,  // ⭐ 使用 step_id
    step_number: stepNumber,  // 保留（兼容性）
    component: componentNameInput.value || componentName,  // 统一使用输入框的名称
    welding_info: {
      required: true,
      welding_type: '',
      weld_size: '',
      welding_position: ''
    }
  })
}

const removeWeldingRequirement = (index: number) => {
  editData.value.welding_requirements.splice(index, 1)
}

// 添加/删除安全警告
const addSafetyWarning = () => {
  const currentStep = currentStepData.value
  const stepNumber = currentStep?.step_number || 1
  const componentName = currentStep?.component_name || ''

  console.log('➕ [添加安全警告]', { stepNumber, componentName })

  editData.value.safety_warnings.push({
    step_number: stepNumber,
    component: componentNameInput.value || componentName,  // 🔥 修复：使用 component_name 而不是 action
    warning: ''
  })
}

const removeSafetyWarning = (index: number) => {
  editData.value.safety_warnings.splice(index, 1)
}

// 添加/删除FAQ
const addFaqItem = () => {
  editData.value.faq_items.push({ question: '', answer: '' })
}

const removeFaqItem = (index: number) => {
  editData.value.faq_items.splice(index, 1)
}

// 保存修改到草稿（只更新当前步骤的数据）
// 🔧 修复：基于原始数据快照进行精确替换，避免数据丢失和重复
const saveDraft = async () => {
  try {
    saving.value = true

    const currentStep = currentStepData.value
    if (!currentStep) {
      ElMessage.error('当前步骤数据不存在')
      return
    }

    const currentStepNumber = currentStep.step_number
    const newComponentName = componentNameInput.value.trim() || currentStep.component_name || ''

    // 更新manualData
    const updatedData = { ...manualData.value }
    const newDescription = (editData.value.step_description || '').trim()

    // 统一同步名称到编辑表单，避免多个来源不一致
    editData.value.welding_requirements = editData.value.welding_requirements.map(req => ({
      ...req,
      component: newComponentName
    }))
    editData.value.safety_warnings = editData.value.safety_warnings.map(w => ({
      ...w,
      component: newComponentName
    }))

    // ========== 更新焊接要求（只保存到步骤内嵌字段） ==========
    const currentStepId = currentStep.step_id || ''

    console.log('💾 [保存组件名称]')
    console.log('  - 当前步骤ID:', currentStepId)
    console.log('  - 原组件名称:', currentStep.component_name)
    console.log('  - 新组件名称:', newComponentName)
    console.log('  - 焊接要求数量:', editData.value.welding_requirements.length)

    // 过滤有效的焊接数据
    const validWeldingReqs = editData.value.welding_requirements
      .filter(r => r.welding_info && (r.welding_info.welding_type || r.welding_info.weld_size || r.welding_info.welding_position))

    // 更新步骤内嵌的 welding 字段和 component_name
    let stepUpdated = false

    // 更新组件装配步骤
    if (updatedData.component_assembly) {
      for (const component of updatedData.component_assembly) {
        if (component.steps) {
          for (const step of component.steps) {
            if (step.step_id === currentStepId) {
              console.log('  ✅ 找到匹配的步骤，准备更新...')
              console.log('  - 更新前 component.component_name:', component.component_name)

              if (newDescription) {
                step.description = newDescription
                step.operation = newDescription
              }

              // 更新焊接数据
              if (validWeldingReqs.length > 0) {
                step.welding = validWeldingReqs[0].welding_info
              } else {
                delete step.welding
              }

              // ✅ 更新组件级别的 component_name（前端显示用的是这个）
              component.component_name = newComponentName

              console.log('  - 更新后 component.component_name:', component.component_name)
              stepUpdated = true
              break
            }
          }
        }
        if (stepUpdated) break
      }
    }

    // 更新产品装配步骤
    if (!stepUpdated && updatedData.product_assembly?.steps) {
      for (const step of updatedData.product_assembly.steps) {
        if (step.step_id === currentStepId) {
          if (newDescription) {
            step.description = newDescription
            step.operation = newDescription
          }
          // 更新焊接数据
          if (validWeldingReqs.length > 0) {
            step.welding = validWeldingReqs[0].welding_info
          } else {
            delete step.welding
          }
          // 更新组件名称（如果用户修改了）
          step.component_name = newComponentName
          stepUpdated = true
          break
        }
      }
    }

    // ========== 更新安全警告（只保存到步骤内嵌字段） ==========
    // 过滤有效的安全警告
    const validSafetyWarnings = editData.value.safety_warnings
      .filter(w => w.warning && w.warning.trim())
      .map(w => w.warning)

    // 更新步骤内嵌的 safety_warnings 字段和 component_name
    stepUpdated = false

    // 更新组件装配步骤
    if (updatedData.component_assembly) {
      for (const component of updatedData.component_assembly) {
        if (component.steps) {
          for (const step of component.steps) {
            if (step.step_id === currentStepId) {
              step.safety_warnings = validSafetyWarnings
              // ✅ 更新组件级别的 component_name（前端显示用的是这个）
              component.component_name = newComponentName
              stepUpdated = true
              break
            }
          }
        }
        if (stepUpdated) break
      }
    }

    // 更新产品装配步骤
    if (!stepUpdated && updatedData.product_assembly?.steps) {
      for (const step of updatedData.product_assembly.steps) {
        if (step.step_id === currentStepId) {
          step.safety_warnings = validSafetyWarnings
          // 更新组件名称（优先使用安全警告中的组件名称）
          step.component_name = newComponentName
          stepUpdated = true
          break
        }
      }
    }

    // ========== 更新质检要求 ==========
    // 使用 step_id 精确匹配当前步骤
    stepUpdated = false

    // 更新组件装配步骤中的质检要求
    if (updatedData.component_assembly) {
      for (const component of updatedData.component_assembly) {
        if (component.steps) {
          for (const step of component.steps) {
            if (step.step_id === currentStepId) {
              step.quality_check = editData.value.quality_check
              stepUpdated = true
              break
            }
          }
        }
        if (stepUpdated) break
      }
    }

    // 更新产品装配步骤中的质检要求
    if (!stepUpdated && updatedData.product_assembly?.steps) {
      for (const step of updatedData.product_assembly.steps) {
        if (step.step_id === currentStepId) {
          step.quality_check = editData.value.quality_check
          stepUpdated = true
          break
        }
      }
    }

    // ========== 更新FAQ（全局） ==========
    if (!updatedData.safety_and_faq) {
      updatedData.safety_and_faq = {}
    }
    updatedData.safety_and_faq.faq_items = editData.value.faq_items.filter(
      f => f.question.trim() && f.answer.trim()
    )

    const currentEditVersion = manualData.value?._edit_version ?? 0
    updatedData._edit_version = currentEditVersion

    // 调用后端API保存草稿
    const response = await axios.post(`/api/manual/${props.taskId}/save-draft`, {
      manual_data: updatedData
    })

    if (response.data.success) {
      updatedData._edit_version = currentEditVersion + 1
      // 更新本地数据到草稿态
      setManualDataValue(updatedData)

      // ✅ 立即显示草稿提示条
      isDraftMode.value = true

      const cacheDraftKey = `current_manual_draft_${props.taskId}`
      localStorage.setItem(cacheDraftKey, JSON.stringify(updatedData))

      ElMessage.success('草稿已保存')
      showEditDialog.value = false

      console.log('✅ [草稿保存成功]')
      console.log('  - lastUpdated:', response.data.lastUpdated)
    }
  } catch (error: any) {
    console.error('❌ [保存失败]:', error)
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

const openPublishDialog = () => {
  if (!isAdmin.value) {
    ElMessage.warning('请先登录管理员')
    return
  }
  publishForm.value.changelog = ''
  showPublishDialog.value = true
}

const refreshManualFromServer = async () => {
  try {
    let data
    // 管理员模式下优先获取草稿，确保编辑操作后能看到最新数据
    if (isAdmin.value) {
      try {
        const draftResp = await axios.get(`/api/manual/${props.taskId}/draft`)
        data = draftResp.data
        isDraftMode.value = true  // 标记为草稿模式
        console.log('✅ 管理员模式：从草稿加载数据')
      } catch (e) {
        // 草稿不存在，fallback 到已发布版本
        const resp = await axios.get(`/api/manual/${props.taskId}`)
        data = resp.data
        isDraftMode.value = false  // 非草稿模式
        console.log('✅ 管理员模式：草稿不存在，从已发布版本加载')
      }
    } else {
      // 普通用户：只获取已发布版本
      const resp = await axios.get(`/api/manual/${props.taskId}`)
      data = resp.data
      isDraftMode.value = false
    }
    const cacheKey = `current_manual_${props.taskId}`
    localStorage.setItem(cacheKey, JSON.stringify(data))
    setManualDataValue(data)
    currentStepIndex.value = 0
  } catch (error: any) {
    console.error('❌ 刷新数据失败:', error)
    ElMessage.error('刷新失败: ' + (error.response?.data?.detail || error.message))
  }
}

const openInsertDialog = () => {
  if (!isAdmin.value) {
    ElMessage.warning('请先登录管理员')
    return
  }
  insertAfterStepId.value = currentStepData.value?.step_id || null
  insertAction.value = ''
  insertDescription.value = ''
  showInsertDialog.value = true
}

const handleInsertStep = async () => {
  if (!currentStepData.value) {
    ElMessage.error('当前步骤数据不存在')
    return
  }
  const chapterType = currentStepData.value.chapter_type
  const componentCode = currentStepData.value.component_code
  const editVersion = manualData.value?._edit_version ?? 0

  const drawings = currentStepData.value.drawings ||
                   currentStepData.value.pdf_images ||
                   currentStepData.value.technical_drawings ||
                   currentStepData.value.drawing_images ||
                   []

  const payload = {
    chapter_type: chapterType,
    component_code: componentCode,
    after_step_id: insertAfterStepId.value,
    new_step: {
      action: insertAction.value || '新步骤',
      title: insertAction.value || '新步骤',
      description: insertDescription.value || '',
      parts_used: currentStepData.value.parts_used || [],
      drawings
    },
    edit_version: editVersion
  }

  try {
    inserting.value = true
    const resp = await axios.post(`/api/manual/${props.taskId}/steps/insert`, payload)
    ElMessage.success('插入成功')
    showInsertDialog.value = false
    await refreshManualFromServer()
    await nextTick()
    const newIndex = allSteps.value.findIndex(s => s.step_id === resp.data.step_id)
    if (newIndex >= 0) {
      currentStepIndex.value = newIndex
    }
  } catch (error: any) {
    console.error('❌ 插入失败:', error)
    ElMessage.error('插入失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    inserting.value = false
  }
}

const confirmDeleteCurrentStep = async () => {
  if (!currentStepData.value) {
    ElMessage.error('当前步骤数据不存在')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除步骤${currentStepData.value.step_number}「${currentStepData.value.action || '未命名'}」吗？`,
      '删除确认',
      { type: 'warning' }
    )
    await handleDeleteStep(currentStepData.value.step_id)
  } catch (error) {
    // 用户取消
  }
}

const handleDeleteStep = async (stepId: string) => {
  if (!stepId) return
  const editVersion = manualData.value?._edit_version ?? 0
  try {
    deletingStep.value = true
    await axios.delete(`/api/manual/${props.taskId}/steps/${stepId}`, {
      params: { edit_version: editVersion }
    })
    ElMessage.success('删除成功')
    await refreshManualFromServer()
    if (currentStepIndex.value >= allSteps.value.length) {
      currentStepIndex.value = Math.max(0, allSteps.value.length - 1)
    }
  } catch (error: any) {
    console.error('❌ 删除失败:', error)
    ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    deletingStep.value = false
  }
}


const confirmPublish = async () => {
  if (!publishForm.value.changelog.trim()) {
    ElMessage.warning('请填写版本说明')
    return
  }

  try {
    publishing.value = true
    const response = await axios.post(`/api/manual/${props.taskId}/publish`, {
      changelog: publishForm.value.changelog.trim()
    })
    ElMessage.success(`发布成功，版本: ${response.data.version}`)
    showPublishDialog.value = false
    publishForm.value.changelog = ''
    isDraftMode.value = false  // 发布后退出草稿模式
    localStorage.removeItem(`current_manual_draft_${props.taskId}`)
    await refreshManualFromServer()
    await init3DViewerAndModel()
  } catch (error: any) {
    console.error('❌ 发布失败', error)
    ElMessage.error('发布失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    publishing.value = false
  }
}

const goHistory = () => {
  router.push(`/version-history/${props.taskId}`)
}

// 退出历史版本预览（关闭当前标签页）
const exitHistoryPreview = () => {
  window.close()
}

// ============ 下拉菜单命令处理 ============

const handleEditCommand = (command: string) => {
  switch (command) {
    case 'editContent':
      showEditDialog.value = true
      break
    case 'insertStep':
      openInsertDialog()
      break
    case 'deleteStep':
      confirmDeleteCurrentStep()
      break
  }
}

const handleVersionCommand = (command: string) => {
  switch (command) {
    case 'publish':
      openPublishDialog()
      break
    case 'history':
      goHistory()
      break
  }
}

// ============ 丢弃草稿功能 ============

const handleDiscardDraft = async () => {
  try {
    await ElMessageBox.confirm(
      '确定丢弃所有未发布的修改吗？此操作不可撤销。',
      '丢弃草稿确认',
      { type: 'warning', confirmButtonText: '确定丢弃', cancelButtonText: '取消' }
    )

    discardingDraft.value = true
    await axios.delete(`/api/manual/${props.taskId}/draft`)
    ElMessage.success('草稿已丢弃')
    isDraftMode.value = false

    // 重新加载已发布版本
    const resp = await axios.get(`/api/manual/${props.taskId}`)
    setManualDataValue(resp.data)
    localStorage.setItem(`current_manual_${props.taskId}`, JSON.stringify(resp.data))
    currentStepIndex.value = 0

    // ✅ 刷新3D显示，让零件颜色恢复到已发布状态
    updateStepDisplay(false)
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('❌ 丢弃草稿失败:', error)
      ElMessage.error('丢弃失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    discardingDraft.value = false
  }
}

// ✅ 加载 step3_glb_inventory.json 获取3D零件实际名称
const loadGlbInventory = async () => {
  if (!props.taskId) return
  try {
    const resp = await axios.get(`/api/manual/${props.taskId}/glb-inventory`)
    const nodeToGeometry = resp.data?.glb_files?.product_total?.node_to_geometry
    if (Array.isArray(nodeToGeometry)) {
      glbNodeToGeometry.value = nodeToGeometry
      console.log(`✅ 加载 glb-inventory 成功，共 ${nodeToGeometry.length} 个零件名称映射`)
    }
  } catch (e) {
    // 文件不存在不影响主流程，只是显示 NAUO 序号
    console.log('📝 glb-inventory 不存在或加载失败，将显示 NAUO 序号')
  }
}

// ✅ 加载数据：历史版本 > 管理员草稿 > 普通已发布
const loadLocalJSON = async () => {
  if (!props.taskId) {
    ElMessage.error('任务ID不存在')
    return
  }
  try {
    // ✅ 先加载 step3_glb_inventory.json（3D零件名称映射）
    await loadGlbInventory()
    // 历史版本模式：从 ?version=v2 参数加载指定版本（只读）
    if (historyVersion.value) {
      try {
        const resp = await axios.get(`/api/manual/${props.taskId}/version/${historyVersion.value}`)
        setManualDataValue(resp.data)
        console.log(`✅ 历史版本模式：加载 ${historyVersion.value} 成功`)
        ElMessage.success(`正在查看历史版本 ${historyVersion.value}`)
        await init3DViewerAndModel()
        return
      } catch (e: any) {
        console.error('❌ 加载历史版本失败:', e)
        ElMessage.error('加载历史版本失败: ' + (e.response?.data?.detail || e.message))
        return
      }
    }

    // 管理员模式：优先从服务器获取草稿，确保看到最新编辑内容
    if (isAdmin.value) {
      try {
        const draftResp = await axios.get(`/api/manual/${props.taskId}/draft`)
        setManualDataValue(draftResp.data)
        isDraftMode.value = true  // 标记为草稿模式
        console.log('✅ 管理员模式：从草稿加载说明书成功')
        ElMessage.success('装配说明书加载成功（草稿模式）！')
        await init3DViewerAndModel()
        return
      } catch (e) {
        console.log('📝 草稿不存在，尝试加载已发布版本')
        isDraftMode.value = false  // 非草稿模式
        // 草稿不存在，继续走普通加载流程
      }
    }

    // 普通用户或草稿不存在：使用缓存策略
    const currentManual = localStorage.getItem(`current_manual_${props.taskId}`)
    if (currentManual) {
      const cached = JSON.parse(currentManual)

      // 发送HEAD请求检查版本号和更新时间
      try {
        const response = await axios.head(`/api/manual/${props.taskId}/version`)
        const serverVersion = response.headers['x-manual-version']
        const serverLastUpdated = response.headers['x-manual-lastupdated'] || ''

        console.log(`📌 缓存版本: ${cached.version}, 服务器版本: ${serverVersion}`)
        console.log(`📌 缓存更新时间: ${cached.lastUpdated}, 服务器更新时间: ${serverLastUpdated}`)

        // ✅ 同时比较version和lastUpdated，两者都一致才使用缓存
        const versionMatch = cached.version === serverVersion
        const lastUpdatedMatch = cached.lastUpdated === serverLastUpdated

        if (versionMatch && lastUpdatedMatch) {
          // 版本和更新时间都一致，使用缓存
          setManualDataValue(cached)
          console.log('✅ 从缓存加载说明书成功 (版本和时间戳一致):', manualData.value)
          console.log('📋 manualData的所有字段:', Object.keys(manualData.value))

          ElMessage.success('装配说明书加载成功！')

          // ✅ 数据加载完成后初始化3D
          await init3DViewerAndModel()
          return
        } else {
          console.log(`⚠️ 缓存失效，重新从API加载 (版本匹配: ${versionMatch}, 时间匹配: ${lastUpdatedMatch})`)
        }
      } catch (error) {
        console.warn('版本检查失败,使用缓存数据', error)
        setManualDataValue(cached)
        console.log('✅ 从缓存加载说明书成功 (版本检查失败):', manualData.value)
        ElMessage.success('装配说明书加载成功！')
        await init3DViewerAndModel()
        return
      }
    }

    // 版本不一致或无缓存，从后端 API 获取已发布版本
    const response = await axios.get(`/api/manual/${props.taskId}`)
    setManualDataValue(response.data)

    // 保存到 localStorage（按任务隔离）
    const cachePublishedKey = `current_manual_${props.taskId}`
    localStorage.setItem(cachePublishedKey, JSON.stringify(manualData.value))

    console.log('✅ 从API加载说明书成功:', manualData.value)
    console.log('📋 manualData的所有字段:', Object.keys(manualData.value))

    ElMessage.success('装配说明书加载成功！')

    // ✅ 数据加载完成后初始化3D
    await init3DViewerAndModel()
  } catch (error: any) {
    console.error('❌ 加载失败:', error)
    ElMessage.error('加载失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

const previousStep = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
  }
}

const nextStep = () => {
  if (currentStepIndex.value < totalSteps.value - 1) {
    currentStepIndex.value++
  }
}

// 自动播放：每5秒切换到下一步，到最后一步停止
const toggleAutoPlay = () => {
  if (isAutoPlaying.value) {
    // 停止播放
    stopAutoPlay()
  } else {
    // 开始播放
    startAutoPlay()
  }
}

const startAutoPlay = () => {
  // 如果已经是最后一步，不启动
  if (currentStepIndex.value >= totalSteps.value - 1) {
    ElMessage.info('已经是最后一步了')
    return
  }

  isAutoPlaying.value = true
  autoPlayTimer = setInterval(() => {
    if (currentStepIndex.value < totalSteps.value - 1) {
      currentStepIndex.value++
    } else {
      // 到达最后一步，自动停止
      stopAutoPlay()
      ElMessage.success('播放完成')
    }
  }, 5000) // 5秒间隔
}

const stopAutoPlay = () => {
  isAutoPlaying.value = false
  if (autoPlayTimer) {
    clearInterval(autoPlayTimer)
    autoPlayTimer = null
  }
}

const goToStep = (index: number) => {
  currentStepIndex.value = index
}

const getImportanceType = (importance: string) => {
  const map: any = { '关键': 'danger', '重要': 'warning', '一般': 'info' }
  return map[importance] || 'info'
}

const getSeverityType = (severity: string) => {
  const map: any = { '高': 'error', '中': 'warning', '低': 'info' }
  return map[severity] || 'warning'
}

const init3DViewer = () => {
  console.log('🎬 开始初始化3D查看器...')

  if (!modelContainer.value) {
    console.error('❌ modelContainer 不存在')
    return
  }

  const container = modelContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  console.log('📐 容器尺寸:', { width, height })

  if (width === 0 || height === 0) {
    viewerInitAttempts += 1
    if (viewerInitAttempts <= 5) {
      console.warn(`⏳ 容器尺寸为0，等待重试 (${viewerInitAttempts}/5)...`)
      setTimeout(() => init3DViewer(), 200)
    } else {
      console.error('❌ 容器尺寸为0，重试多次仍失败，无法初始化3D')
    }
    return
  }
  viewerInitAttempts = 0

  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf0f2f5)
  console.log('✅ 场景创建成功')

  // 创建相机
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
  camera.position.set(500, 500, 500)

  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ antialias: !isMobile.value })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile.value ? 2 : 2))
  container.appendChild(renderer.domElement)
  console.log('✅ 渲染器创建成功，已添加到DOM')

  // 添加光源（增强亮度）
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.2)  // 环境光增强到1.2
  scene.add(ambientLight)

  const directionalLight1 = new THREE.DirectionalLight(0xffffff, 1.0)  // 主光源
  directionalLight1.position.set(100, 100, 50)
  scene.add(directionalLight1)

  const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.6)  // 补光
  directionalLight2.position.set(-100, 50, -50)
  scene.add(directionalLight2)

  const directionalLight3 = new THREE.DirectionalLight(0xffffff, 0.4)  // 顶部补光
  directionalLight3.position.set(0, 200, 0)
  scene.add(directionalLight3)

  // 添加控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // 添加底部地面网格（初始位置，会在模型加载后调整）
  const gridSize = 5000  // 大网格
  gridHelper = new THREE.GridHelper(gridSize, 50, 0x888888, 0xcccccc)
  gridHelper.position.y = -1000  // 临时位置
  scene.add(gridHelper)

  // 动画循环
  const animate = () => {
    requestAnimationFrame(animate)
    if (controls) controls.update()
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()
  console.log('🎬 动画循环已启动')

  // ✅ 调试：暴露到window对象
  ;(window as any).__three_debug__ = { scene, camera, renderer, controls }

  // 窗口大小调整
  const handleResize = () => {
    if (!container || !camera || !renderer) return
    const width = container.clientWidth
    const height = container.clientHeight
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile.value ? 2 : 2))
  }
  window.addEventListener('resize', handleResize)

  // ✅ 初始化零件交互功能（射线检测、鼠标事件）
  initPartInteraction()
}

const load3DModel = async () => {
  console.log('🎨 开始加载3D模型...')

  if (!scene) {
    console.error('❌ scene 不存在，无法加载模型')
    return
  }

  if (!manualData.value) {
    console.error('❌ manualData 不存在，无法获取GLB路径')
    return
  }

  if (!allSteps.value.length) {
    console.warn('⚠️ 没有步骤数据，跳过3D模型加载')
    return
  }

  try {
    const loader = new GLTFLoader()

    // ✅ 获取当前步骤对应的GLB文件
    const currentStep = allSteps.value[currentStepIndex.value]
    const glbFile = currentStep?.glb_file

    if (!glbFile) {
      console.warn(`⚠️ 步骤${currentStepIndex.value + 1}缺少glb_file，跳过3D加载`)
      return
    }

    // ✅ 构建完整的GLB文件路径（使用相对路径，支持远程访问）
    const glbPath = `/api/manual/${props.taskId}/glb/${glbFile}`
    console.log('📦 加载3D模型:', glbPath)
    console.log('📋 当前步骤:', currentStepIndex.value + 1, '/', allSteps.value.length)
    console.log('📋 GLB文件:', glbFile)

    const gltf = await loader.loadAsync(glbPath)
    console.log('✅ GLB文件加载成功:', gltf)

    model = gltf.scene

    // 先不保存位置，等模型居中后再保存
    let meshCount = 0
    const meshNames: string[] = []
    model.traverse((child: any) => {
      if (child.isMesh) {
        meshCount++
        meshNames.push(child.name)

        // 创建新的高对比度材质（天蓝色，清晰锐利）
        const brightMaterial = new THREE.MeshStandardMaterial({
          color: 0x4A90E2,        // 天蓝色
          metalness: 0.5,
          roughness: 0.4,
          side: THREE.DoubleSide  // 双面渲染
        })

        child.material = brightMaterial
        meshOriginalMaterials.set(child.name, brightMaterial.clone())
      }
    })

    console.log('🔍 模型中的mesh数量:', meshCount)
    console.log('🔍 前20个mesh名称:', meshNames.slice(0, 20))

    // 计算模型边界并居中
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())

    console.log('📏 模型尺寸:', {
      size: { x: size.x, y: size.y, z: size.z },
      center: { x: center.x, y: center.y, z: center.z }
    })

    // ✅ 如果模型太小（单位可能是米，但实际是毫米建模），放大倍数
    const maxDimOriginal = Math.max(size.x, size.y, size.z)
    let scaleFactor = 1

    // 根据模型尺寸自动计算放大倍数，目标是让模型达到1500-2000单位（根据图纸1830mm）
    if (maxDimOriginal < 10) {
      scaleFactor = 1000000  // 如果小于10，放大100万倍（模型单位可能是米）
    } else if (maxDimOriginal < 100) {
      scaleFactor = 10000   // 如果小于100，放大1万倍
    } else if (maxDimOriginal < 1000) {
      scaleFactor = 1000    // 如果小于1000，放大1000倍
    }

    if (scaleFactor > 1) {
      console.warn(`⚠️ 模型太小（${maxDimOriginal.toFixed(6)}），放大${scaleFactor}倍`)
      model.scale.set(scaleFactor, scaleFactor, scaleFactor)
      // 重新计算边界
      box.setFromObject(model)
      box.getCenter(center)
      box.getSize(size)
      console.log('📏 放大后的模型尺寸:', {
        size: { x: size.x, y: size.y, z: size.z },
        center: { x: center.x, y: center.y, z: center.z },
        scaleFactor
      })
    }

    // 移动模型到中心
    model.position.sub(center)

    // ✅ 模型居中后，保存每个mesh的世界坐标位置和爆炸方向（世界坐标系）
    const worldCenter = new THREE.Vector3(0, 0, 0) // 已经居中到(0,0,0)
    let nearCenterCount = 0
    const samplePositions: any[] = []

    model.traverse((child: any) => {
      if (child.isMesh) {
        // 保存本地坐标位置（兼容旧逻辑）
        const localPos = child.position.clone()
        meshOriginalPositions.set(child.name, localPos)

        // ✅ 计算世界坐标位置
        const worldPos = new THREE.Vector3()
        child.getWorldPosition(worldPos)
        meshWorldOriginalPositions.set(child.uuid, worldPos.clone())

        // 计算并保存爆炸方向（从中心指向零件，纯径向，使用世界坐标）
        const directionWorld = worldPos.clone().sub(worldCenter)
        const distance = directionWorld.length()

        // 收集前10个零件的位置信息用于调试
        if (samplePositions.length < 10) {
          samplePositions.push({
            name: child.name,
            localPos: `(${localPos.x.toFixed(3)}, ${localPos.y.toFixed(3)}, ${localPos.z.toFixed(3)})`,
            worldPos: `(${worldPos.x.toFixed(3)}, ${worldPos.y.toFixed(3)}, ${worldPos.z.toFixed(3)})`,
            distance: distance.toFixed(6),
            parentName: child.parent?.name || 'unknown'
          })
        }

        if (distance < 1e-6) {
          // 如果零件非常接近中心点，使用均匀随机方向避免重叠
          const theta = Math.random() * Math.PI * 2
          const phi = Math.random() * Math.PI
          directionWorld.set(
            Math.sin(phi) * Math.cos(theta),
            Math.cos(phi),
            Math.sin(phi) * Math.sin(theta)
          )
          nearCenterCount++
        } else {
          directionWorld.normalize()
        }

        meshExplodeDirections.set(child.name, directionWorld.clone()) // 兼容旧逻辑（按名称）
        meshWorldExplodeDirections.set(child.uuid, directionWorld)
      }
    })
    console.log('✅ 已保存', meshWorldOriginalPositions.size, '个mesh的世界位置和爆炸方向')
    console.log('📍 前10个零件的位置信息:', samplePositions)
    if (nearCenterCount > 0) {
      console.log(`⚠️ ${nearCenterCount} 个零件非常接近中心，使用随机方向`)
    }

    // 调整相机位置以适应模型
    const maxDim = Math.max(size.x, size.y, size.z)
    console.log('📏 最大尺寸:', maxDim)

    const fov = camera!.fov * (Math.PI / 180)
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2))
    cameraZ *= 2.5 // 增加距离，确保能看到

    console.log('📷 计算的相机距离:', cameraZ)

    // ✅ 如果计算出的距离太小（模型单位可能是毫米），使用固定距离
    if (cameraZ < 10) {
      console.warn('⚠️ 相机距离太小，使用固定距离')
      cameraZ = Math.max(maxDim * 3, 1000) // 至少1000单位
    }

    console.log('📷 最终相机距离:', cameraZ)

    camera!.position.set(cameraZ * 0.7, cameraZ * 0.5, cameraZ * 0.7)
    camera!.lookAt(0, 0, 0)

    if (controls) {
      controls.target.set(0, 0, 0)
      controls.update()
    }

    console.log('📷 相机位置:', camera!.position)
    console.log('🎯 控制器目标:', controls?.target)

    scene.add(model)
    console.log('✅ 3D模型已添加到场景')
    console.log('📊 模型信息:', {
      meshCount: meshOriginalPositions.size,
      boundingBox: size,
      center,
      cameraPosition: camera!.position,
      modelPosition: model.position
    })

    // ✅ 调整网格位置，紧贴模型底部
    if (gridHelper) {
      const modelBox = new THREE.Box3().setFromObject(model)
      const modelMin = modelBox.min
      gridHelper.position.y = modelMin.y  // 网格Y坐标 = 模型最低点Y坐标
      console.log('✅ 网格已调整到模型底部，Y =', modelMin.y)
    }

    // ✅ 调试：暴露model到window对象
    ;(window as any).__three_debug__.model = model

    ElMessage.success('3D模型加载成功！')

    // 初始化累积归位与高亮
    updateStepDisplay(false)
  } catch (error: any) {
    console.error('❌ 3D模型加载失败:', error)
    ElMessage.error('3D模型加载失败: ' + (error.message || '未知错误'))
  }
}

// 切换GLB模型
const switchGLBModel = async (glbFile: string) => {
  console.log('🔄 开始切换GLB模型:', glbFile)

  if (!scene) {
    console.error('❌ scene 不存在，无法切换模型')
    return
  }

  if (!glbFile) {
    console.warn('⚠️ 当前步骤缺少glb_file，跳过模型切换')
    return
  }

  try {
    // 1. 清除旧模型
    if (model) {
      console.log('🗑️ 清除旧模型')
      scene.remove(model)
      model.traverse((child: any) => {
        if (child.isMesh) {
          child.geometry?.dispose()
          child.material?.dispose()
        }
      })
    }

    // 2. 清空材质缓存
    meshOriginalMaterials.clear()
    meshOriginalPositions.clear()
    // ✅ 清空世界坐标缓存
    meshWorldOriginalPositions.clear()
    meshWorldExplodeDirections.clear()

    // 3. 加载新模型
    const loader = new GLTFLoader()
    const glbPath = `/api/manual/${props.taskId}/glb/${glbFile}`
    console.log('📦 加载新模型:', glbPath)

    const gltf = await loader.loadAsync(glbPath)
    console.log('✅ 新模型加载成功')

    model = gltf.scene

    // 4. 初始化材质
    let meshCount = 0
    model.traverse((child: any) => {
      if (child.isMesh) {
        meshCount++
        const brightMaterial = new THREE.MeshStandardMaterial({
          color: 0x4A90E2,
          metalness: 0.5,
          roughness: 0.4,
          side: THREE.DoubleSide
        })
        child.material = brightMaterial
        meshOriginalMaterials.set(child.name, brightMaterial.clone())
        meshOriginalPositions.set(child.name, child.position.clone())
      }
    })

    console.log('🔍 新模型mesh数量:', meshCount)

    // 5. 居中和缩放
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())

    const maxDimOriginal = Math.max(size.x, size.y, size.z)
    let scaleFactor = 1

    if (maxDimOriginal < 10) {
      scaleFactor = 1000000
    } else if (maxDimOriginal < 100) {
      scaleFactor = 10000
    } else if (maxDimOriginal < 1000) {
      scaleFactor = 1000
    }

    if (scaleFactor > 1) {
      console.log(`⚠️ 模型太小（${maxDimOriginal.toFixed(6)}），放大${scaleFactor}倍`)
      model.scale.set(scaleFactor, scaleFactor, scaleFactor)
      box.setFromObject(model)
      box.getCenter(center)
      box.getSize(size)
    }

    model.position.set(-center.x, -center.y, -center.z)

    // ✅ 6. 模型居中后，保存每个mesh的世界坐标位置和爆炸方向（世界坐标系）
    const worldCenter = new THREE.Vector3(0, 0, 0) // 已经居中到(0,0,0)
    let nearCenterCount = 0
    const samplePositions: any[] = []

    model.traverse((child: any) => {
      if (child.isMesh) {
        // ✅ 计算世界坐标位置
        const worldPos = new THREE.Vector3()
        child.getWorldPosition(worldPos)
        meshWorldOriginalPositions.set(child.uuid, worldPos.clone())

        // 计算并保存爆炸方向（从中心指向零件，纯径向，使用世界坐标）
        const directionWorld = worldPos.clone().sub(worldCenter)
        const distance = directionWorld.length()

        // 收集前10个零件的位置信息用于调试
        if (samplePositions.length < 10) {
          samplePositions.push({
            name: child.name,
            worldPos: `(${worldPos.x.toFixed(3)}, ${worldPos.y.toFixed(3)}, ${worldPos.z.toFixed(3)})`,
            distance: distance.toFixed(6),
            parentName: child.parent?.name || 'unknown'
          })
        }

        if (distance < 1e-6) {
          // 如果零件非常接近中心点，使用均匀随机方向避免重叠
          const theta = Math.random() * Math.PI * 2
          const phi = Math.random() * Math.PI
          directionWorld.set(
            Math.sin(phi) * Math.cos(theta),
            Math.cos(phi),
            Math.sin(phi) * Math.sin(theta)
          )
          nearCenterCount++
        } else {
          directionWorld.normalize()
        }

        meshExplodeDirections.set(child.name, directionWorld.clone()) // 兼容旧逻辑（按名称）
        meshWorldExplodeDirections.set(child.uuid, directionWorld)
      }
    })
    console.log('✅ 已保存', meshWorldOriginalPositions.size, '个mesh的世界位置和爆炸方向')
    console.log('📍 前10个零件的位置信息:', samplePositions)
    if (nearCenterCount > 0) {
      console.log(`⚠️ ${nearCenterCount} 个零件非常接近中心，使用随机方向`)
    }

    // 7. 调整相机
    const maxDim = Math.max(size.x, size.y, size.z)
    let cameraZ = maxDim * 2.5

    if (cameraZ < 100) {
      cameraZ = Math.max(maxDim * 3, 1000)
    }

    camera!.position.set(cameraZ * 0.7, cameraZ * 0.5, cameraZ * 0.7)
    camera!.lookAt(0, 0, 0)

    if (controls) {
      controls.target.set(0, 0, 0)
      controls.update()
    }

    // 8. 添加到场景
    scene.add(model)
    console.log('✅ 新模型已添加到场景')

    // 9. 调整网格
    if (gridHelper) {
      const modelBox = new THREE.Box3().setFromObject(model)
      gridHelper.position.y = modelBox.min.y
    }

    // 10. 初始化显示状态
    isExploded.value = true
    updateStepDisplay(false)

    ElMessage.success(`已切换到${glbFile}`)
  } catch (error: any) {
    console.error('❌ 切换模型失败:', error)
    ElMessage.error('切换模型失败: ' + (error.message || '未知错误'))
  }
}

// 动画过渡到目标位置
const animateMeshPosition = (mesh: THREE.Mesh, targetLocal: THREE.Vector3, duration = 400) => {
  const startPos = mesh.position.clone()
  const start = performance.now()

  const step = (now: number) => {
    const t = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - t, 3) // easeOutCubic
    mesh.position.lerpVectors(startPos, targetLocal, eased)
    if (t < 1) {
      requestAnimationFrame(step)
    }
  }

  requestAnimationFrame(step)
}

// 累积归位 + 高亮：当前步高亮，已装配正常色，未装配半透明且保持爆炸
const updateStepDisplay = (animate = true) => {
  if (!model) return

  const assembledSet = new Set(assembledNodeNames.value)
  const currentSet = new Set(currentStepNodeNames.value)

  // 材质定义
  const highlightMaterial = new THREE.MeshStandardMaterial({
    color: 0xffff00,
    emissive: 0xffaa00,
    emissiveIntensity: 0.8,
    metalness: 0.3,
    roughness: 0.4
  })
  const unassembledMaterial = new THREE.MeshStandardMaterial({
    color: 0x888888,
    opacity: 0.35,
    transparent: true,
    metalness: 0.2,
    roughness: 0.6
  })

  // 基准爆炸距离
  const box = new THREE.Box3().setFromObject(model)
  const size = new THREE.Vector3()
  box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z)
  const explodeDistanceBase = isExploded.value ? maxDim * (explodeScale.value / 100 || 0.25) : 0

  let processed = 0
  model.traverse((child: any) => {
    if (!child.isMesh) return
    const originalWorldPos = meshWorldOriginalPositions.get(child.uuid)
    const explodeDir = meshWorldExplodeDirections.get(child.uuid)
    if (!originalWorldPos || !explodeDir) return

    // ✅ 检查是否是已删除的零件
    const meshKey = child.name || child.uuid
    if (deletedParts.value.has(meshKey)) {
      child.visible = false
      return  // 跳过后续处理
    }

    const isCurrent = currentSet.has(child.name)
    const isAssembled = assembledSet.has(child.name)

    // ✅ 先获取手动状态（位置和颜色都需要用）
    // meshKey 已在上面定义
    const stepId = currentStepData.value?.step_id
    const stepStates = stepId ? partAssemblyStates.value.get(stepId) : null
    let manualStatus = stepStates?.get(meshKey)

    // ✅ 状态继承：如果当前步骤没有手动状态，检查之前步骤
    // 第N步设为"正在装"的零件，在第N+1步及之后应自动变成"已装"
    if (!manualStatus && currentStepIndex.value > 0) {
      for (let i = currentStepIndex.value - 1; i >= 0; i--) {
        const prevStepId = allSteps.value[i]?.step_id
        if (!prevStepId) continue
        const prevStepStates = partAssemblyStates.value.get(prevStepId)
        const prevStatus = prevStepStates?.get(meshKey)
        if (prevStatus === 'installing' || prevStatus === 'installed') {
          manualStatus = 'installed'  // 之前设为正在装/已装，现在视为已装
          break
        }
      }
    }

    // ✅ 位置逻辑：手动状态优先，再用自动逻辑（修复颜色和位置不一致的问题）
    let targetWorld: THREE.Vector3
    if (manualStatus) {
      // 手动状态优先（与 applyPartPosition 逻辑一致）
      if (manualStatus === 'not_installed') {
        // 未装：始终爆炸到指定位置（不受 isExploded 影响）
        const explodeDistance = maxDim * (explodeScale.value / 100 || 0.25)
        targetWorld = originalWorldPos.clone().add(explodeDir.clone().multiplyScalar(explodeDistance))
      } else {
        // 正在装/已装：归位
        targetWorld = originalWorldPos.clone()
      }
    } else {
      // 自动逻辑（原有逻辑）
      targetWorld = isAssembled || isCurrent || explodeDistanceBase === 0
        ? originalWorldPos.clone()
        : originalWorldPos.clone().add(explodeDir.clone().multiplyScalar(explodeDistanceBase))
    }

    const targetLocal = child.parent.worldToLocal(targetWorld.clone())
    if (animate) {
      animateMeshPosition(child, targetLocal, 450)
    } else {
      child.position.copy(targetLocal)
    }

    if (manualStatus) {
      // 使用手动标记的状态和材质
      applyPartStatusMaterial(child, manualStatus)
    } else {
      // 使用原有的自动逻辑
      if (isCurrent) {
        child.material = highlightMaterial.clone()
      } else if (isAssembled) {
        const originMat = meshOriginalMaterials.get(child.name)
        child.material = originMat ? originMat.clone() : new THREE.MeshStandardMaterial({ color: 0x4a90e2 })
        child.material.transparent = false
        child.material.opacity = 1
      } else {
        child.material = unassembledMaterial.clone()
      }
    }
    processed++
  })

  console.log(`🎯 updateStepDisplay -> assembled: ${assembledSet.size}, current: ${currentSet.size}, processed meshes: ${processed}, explodeBase: ${explodeDistanceBase.toFixed(3)}`)
}

// 爆炸视图开关
const toggleExplode = () => {
  if (!model) return
  isExploded.value = !isExploded.value
  updateStepDisplay(true)
}

// 监听爆炸比例变化
watch(explodeScale, () => {
  updateStepDisplay(true)
})

// ============ 零件交互选中功能（管理员专用） ============

// 初始化零件交互功能
const initPartInteraction = () => {
  if (!renderer || !camera || !scene) {
    console.warn('⚠️ 无法初始化零件交互：renderer/camera/scene 未就绪')
    return
  }

  raycaster = new THREE.Raycaster()
  hoverOutlineGroup = new THREE.Group()
  hoverOutlineGroup.name = 'hoverOutlineGroup'
  scene.add(hoverOutlineGroup)

  const canvas = renderer.domElement

  // 鼠标移动 - 悬浮检测（节流 50ms）
  let lastMoveTime = 0
  canvas.addEventListener('mousemove', (event: MouseEvent) => {
    const now = Date.now()
    if (now - lastMoveTime < 50) return
    lastMoveTime = now
    onCanvasMouseMove(event)
  })

  // 鼠标按下 - 记录位置和时间
  canvas.addEventListener('mousedown', onCanvasMouseDown)

  // 鼠标松开 - 判断是否点击
  canvas.addEventListener('mouseup', onCanvasMouseUp)

  console.log('✅ 零件交互功能初始化完成')
}

// 鼠标按下事件
const onCanvasMouseDown = (event: MouseEvent) => {
  mouseDownPosition = { x: event.clientX, y: event.clientY }
  mouseDownTime = Date.now()
}

// 鼠标松开事件
const onCanvasMouseUp = (event: MouseEvent) => {
  const dx = event.clientX - mouseDownPosition.x
  const dy = event.clientY - mouseDownPosition.y
  const distance = Math.sqrt(dx * dx + dy * dy)
  const duration = Date.now() - mouseDownTime

  // 移动距离小于5像素，且按下时间小于300ms，认为是点击
  if (distance < 5 && duration < 300) {
    onCanvasClick(event)
  }
}

// 鼠标移动事件 - 悬浮检测
const onCanvasMouseMove = (event: MouseEvent) => {
  if (!raycaster || !camera || !model || !renderer) return

  // 只有管理员才能使用此功能
  if (!isAdmin.value) return

  const canvas = renderer.domElement
  const rect = canvas.getBoundingClientRect()

  // 计算鼠标在 canvas 中的归一化坐标 (-1 到 1)
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  // 射线检测
  raycaster.setFromCamera(mouse, camera)
  const intersects = raycaster.intersectObjects(model.children, true)

  if (intersects.length > 0) {
    const hitObject = intersects[0].object as THREE.Mesh
    if (hitObject.isMesh && hitObject !== hoveredMesh.value) {
      hoveredMesh.value = hitObject
      updateHoverOutline(hitObject)
    }
  } else {
    if (hoveredMesh.value) {
      hoveredMesh.value = null
      clearHoverOutline()
    }
  }
}

// 点击事件
const onCanvasClick = (event: MouseEvent) => {
  if (!raycaster || !camera || !model || !renderer) return
  if (!isAdmin.value) return  // 只有管理员可用

  const canvas = renderer.domElement
  const rect = canvas.getBoundingClientRect()

  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera)
  const intersects = raycaster.intersectObjects(model.children, true)

  if (intersects.length > 0) {
    const hitObject = intersects[0].object as THREE.Mesh
    if (hitObject.isMesh) {
      selectedMesh.value = hitObject

      // 计算弹窗位置（在点击位置附近）
      statusPopupPosition.value = {
        x: event.clientX,
        y: event.clientY
      }
      showStatusPopup.value = true
      console.log('🎯 选中零件:', hitObject.name || hitObject.uuid)
    }
  } else {
    // 点击空白处关闭弹窗
    closeStatusPopup()
  }
}

// 更新悬浮边框（红色）
const updateHoverOutline = (mesh: THREE.Mesh) => {
  if (!hoverOutlineGroup) return

  // 清除旧边框
  clearHoverOutline()

  try {
    // 创建边框几何体
    const edges = new THREE.EdgesGeometry(mesh.geometry, 15) // 15度阈值
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0xff0000, // 红色
      linewidth: 2
    })
    const lineSegments = new THREE.LineSegments(edges, lineMaterial)

    // 复制 mesh 的世界变换矩阵
    mesh.updateWorldMatrix(true, false)
    lineSegments.applyMatrix4(mesh.matrixWorld)

    hoverOutlineGroup.add(lineSegments)
  } catch (error) {
    console.warn('⚠️ 创建边框失败:', error)
  }
}

// 清除悬浮边框
const clearHoverOutline = () => {
  if (!hoverOutlineGroup) return
  while (hoverOutlineGroup.children.length > 0) {
    const child = hoverOutlineGroup.children[0]
    hoverOutlineGroup.remove(child)
    if (child instanceof THREE.LineSegments) {
      child.geometry.dispose()
      ;(child.material as THREE.Material).dispose()
    }
  }
}

// 关闭状态弹窗
const closeStatusPopup = () => {
  showStatusPopup.value = false
  selectedMesh.value = null
}

// 获取零件当前状态（按当前步骤获取）
const getPartStatus = (mesh: THREE.Mesh | null): AssemblyStatus | null => {
  if (!mesh) return null
  const stepId = currentStepData.value?.step_id
  if (!stepId) return null

  const meshKey = mesh.name || mesh.uuid
  const stepStates = partAssemblyStates.value.get(stepId)
  return stepStates?.get(meshKey) || null
}

// 获取指定步骤的零件状态
const getPartStatusByStep = (stepId: string, meshKey: string): AssemblyStatus | null => {
  const stepStates = partAssemblyStates.value.get(stepId)
  return stepStates?.get(meshKey) || null
}

// 设置零件状态（按当前步骤存储 + 自动保存）
const setPartStatus = (status: AssemblyStatus) => {
  if (!selectedMesh.value) return

  const stepId = currentStepData.value?.step_id
  if (!stepId) {
    console.warn('⚠️ 当前步骤没有 step_id，无法保存状态')
    return
  }

  const meshKey = selectedMesh.value.name || selectedMesh.value.uuid

  // 获取或创建当前步骤的状态Map
  if (!partAssemblyStates.value.has(stepId)) {
    partAssemblyStates.value.set(stepId, new Map())
  }
  const stepStates = partAssemblyStates.value.get(stepId)!
  stepStates.set(meshKey, status)

  // 立即更新该零件的材质
  applyPartStatusMaterial(selectedMesh.value, status)

  // ✅ 根据状态决定零件位置：正在装/已装 → 归位，未装 → 保持爆炸位置
  applyPartPosition(selectedMesh.value, status)

  console.log(`✅ 步骤 "${stepId}" 零件 "${meshKey}" 状态设置为: ${status}`)

  // ✅ 自动保存到草稿（带防抖）
  autoSavePartStates()

  // 关闭弹窗
  closeStatusPopup()
}

// 自动保存零件状态到草稿（防抖500ms）
const autoSavePartStates = () => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }

  autoSaveTimer = setTimeout(async () => {
    try {
      // 将 Map 转换为可序列化的对象
      const statesObj: Record<string, Record<string, AssemblyStatus>> = {}
      partAssemblyStates.value.forEach((stepMap, stepId) => {
        statesObj[stepId] = Object.fromEntries(stepMap)
      })

      // 将 deletedParts Set 转换为数组
      const deletedPartsArr = Array.from(deletedParts.value)

      // 更新 manualData
      const updatedData = {
        ...manualData.value,
        part_assembly_states: statesObj,
        deleted_parts: deletedPartsArr
      }

      // 调用保存草稿API
      const response = await axios.post(`/api/manual/${props.taskId}/save-draft`, {
        manual_data: updatedData
      })

      if (response.data.success) {
        // 更新本地数据
        updatedData._edit_version = (manualData.value?._edit_version ?? 0) + 1
        setManualDataValue(updatedData)

        // ✅ 立即显示草稿提示条
        isDraftMode.value = true

        // 更新缓存
        const cacheDraftKey = `current_manual_draft_${props.taskId}`
        localStorage.setItem(cacheDraftKey, JSON.stringify(updatedData))

        console.log('✅ 零件状态已自动保存到草稿')
      }
    } catch (error: any) {
      console.error('❌ 自动保存零件状态失败:', error)
      // 不显示错误提示，避免干扰用户操作
    }
  }, 500)
}

// 删除零件（全局隐藏）
const deletePart = async () => {
  if (!selectedMesh.value) return

  const meshKey = selectedMesh.value.name || selectedMesh.value.uuid
  const displayName = getPartDisplayName(selectedMesh.value)

  try {
    await ElMessageBox.confirm(
      `确定要删除零件 "${displayName}" 吗？删除后该零件在所有步骤都不会显示。`,
      '删除零件',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 添加到已删除集合
    deletedParts.value.add(meshKey)

    // 隐藏该零件
    selectedMesh.value.visible = false

    // 关闭弹窗
    closeStatusPopup()

    // 自动保存
    autoSavePartStates()

    ElMessage.success(`零件 "${displayName}" 已删除`)
    console.log(`🗑️ 零件已删除: ${meshKey}`)
  } catch {
    // 用户取消
  }
}

// 恢复已删除的零件
const restorePart = (meshKey: string) => {
  // 从已删除集合中移除
  deletedParts.value.delete(meshKey)

  // 找到对应的 mesh 并显示
  if (model) {
    model.traverse((child: any) => {
      if (child.isMesh) {
        const childKey = child.name || child.uuid
        if (childKey === meshKey) {
          child.visible = true
        }
      }
    })
  }

  // 自动保存
  autoSavePartStates()

  const displayName = getDeletedPartDisplayName(meshKey)
  ElMessage.success(`零件 "${displayName}" 已恢复`)
  console.log(`✅ 零件已恢复: ${meshKey}`)
}

// 获取已删除零件的显示名称
const getDeletedPartDisplayName = (meshKey: string): string => {
  // 优先从 glbNodeToGeometry 获取名称
  if (glbNodeToGeometry.value && glbNodeToGeometry.value[meshKey]) {
    return glbNodeToGeometry.value[meshKey]
  }
  return meshKey
}

// 应用状态对应的材质（使用原来的配色）
const applyPartStatusMaterial = (mesh: THREE.Mesh, status: AssemblyStatus) => {
  switch (status) {
    case 'not_installed':
      // 未装：灰色半透明
      mesh.material = new THREE.MeshStandardMaterial({
        color: 0x888888,
        opacity: 0.35,
        transparent: true,
        metalness: 0.2,
        roughness: 0.6
      })
      break
    case 'installing':
      // 正在装：黄色高亮（和原来的 highlightMaterial 一致）
      mesh.material = new THREE.MeshStandardMaterial({
        color: 0xffff00,
        emissive: 0xffaa00,
        emissiveIntensity: 0.8,
        metalness: 0.3,
        roughness: 0.4
      })
      break
    case 'installed':
      // 已装：恢复原始材质或使用蓝色
      const originMat = meshOriginalMaterials.get(mesh.name)
      if (originMat) {
        mesh.material = originMat.clone()
        ;(mesh.material as THREE.MeshStandardMaterial).transparent = false
        ;(mesh.material as THREE.MeshStandardMaterial).opacity = 1
      } else {
        mesh.material = new THREE.MeshStandardMaterial({
          color: 0x4a90e2,
          metalness: 0.5,
          roughness: 0.4
        })
      }
      break
  }
}

// 应用零件位置（归位或弹出）
const applyPartPosition = (mesh: THREE.Mesh, status: AssemblyStatus) => {
  if (!model) return

  const originalWorldPos = meshWorldOriginalPositions.get(mesh.uuid)
  const explodeDir = meshWorldExplodeDirections.get(mesh.uuid)
  if (!originalWorldPos || !explodeDir) return

  // 计算爆炸距离（未装状态始终使用爆炸距离，不受 isExploded 影响）
  const box = new THREE.Box3().setFromObject(model)
  const size = new THREE.Vector3()
  box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z)
  // 未装状态：始终使用爆炸比例计算距离（即使当前是收起视图）
  const explodeDistance = maxDim * (explodeScale.value / 100 || 0.25)

  let targetWorld: THREE.Vector3
  if (status === 'not_installed') {
    // 未装：弹出到爆炸位置
    targetWorld = originalWorldPos.clone().add(explodeDir.clone().multiplyScalar(explodeDistance))
  } else {
    // 正在装/已装：归位到原始位置
    targetWorld = originalWorldPos.clone()
  }

  const targetLocal = mesh.parent!.worldToLocal(targetWorld.clone())
  animateMeshPosition(mesh, targetLocal, 450)
}

// 获取零件显示名称（美化名称）
const getPartDisplayName = (mesh: THREE.Mesh | null): string => {
  if (!mesh) return '未命名零件'

  const name = mesh.name || ''

  // ✅ 优先从 BOM 映射中获取实际零件名称（而非 NAUO 序号）
  if (name && nodeNameToPartName.value.has(name)) {
    return nodeNameToPartName.value.get(name)!
  }

  // 如果名称为空或太短，使用uuid的前8位
  if (!name || name.length < 2) {
    return `零件-${mesh.uuid.substring(0, 8)}`
  }

  // 尝试解码可能的URL编码
  try {
    const decoded = decodeURIComponent(name)
    if (decoded !== name) {
      return decoded
    }
  } catch (e) {
    // 解码失败，使用原名称
  }

  // 如果名称看起来是乱码（非中英文数字），尝试美化
  if (!/[\u4e00-\u9fa5a-zA-Z0-9]/.test(name)) {
    return `零件-${mesh.uuid.substring(0, 8)}`
  }

  return name
}

// 获取零件原始 NAUO 序号（mesh.name）
const getPartNauoName = (mesh: THREE.Mesh | null): string => {
  if (!mesh) return '-'
  return mesh.name || mesh.uuid.substring(0, 8)
}

// ============ 零件交互功能结束 ============

// 线框模式
const toggleWireframe = () => {
  if (!model) return

  isWireframe.value = !isWireframe.value

  model.traverse((child: any) => {
    if (child.isMesh) {
      if (child.material) {
        child.material.wireframe = isWireframe.value
      }
    }
  })
}

// 重置相机
const resetCamera = () => {
  if (!camera || !controls || !model) return

  const box = new THREE.Box3().setFromObject(model)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())

  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = camera.fov * (Math.PI / 180)
  let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2))
  cameraZ *= 1.5

  camera.position.set(cameraZ, cameraZ, cameraZ)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)
  controls.update()
}



// 监听步骤变化，更新高亮和GLB模型
watch(currentStepIndex, async (newIndex, oldIndex) => {
  const newStep = allSteps.value[newIndex]
  const oldStep = allSteps.value[oldIndex]

  // 检查是否需要切换GLB文件
  const newGlbFile = newStep?.glb_file
  const oldGlbFile = oldStep?.glb_file

  console.log(`📋 步骤切换: ${oldIndex + 1} → ${newIndex + 1}`)
  console.log(`📦 GLB文件: ${oldGlbFile || '无'} → ${newGlbFile || '无'}`)

  // ✅ 修复：只要新步骤有GLB文件，且与旧步骤不同，就切换
  // 不再要求oldGlbFile必须存在（解决首次加载和步骤缺失glb_file的问题）
  if (newGlbFile && newGlbFile !== oldGlbFile) {
    console.log(`🔄 切换GLB模型: ${oldGlbFile || '无'} → ${newGlbFile}`)
    await switchGLBModel(newGlbFile)
  } else if (!newGlbFile) {
    console.warn(`⚠️ 步骤${newIndex + 1}缺少glb_file字段，无法加载3D模型`)
  } else {
    console.log(`✅ GLB文件未变化，无需切换`)
  }

  updateStepDisplay(true)
})

onMounted(() => {
  // 检查sessionStorage中的登录状态
  const adminStatus = sessionStorage.getItem('isAdmin')
  if (adminStatus === 'true') {
    isAdmin.value = true
  }

  // ✅ 只需要加载数据，3D初始化会在数据加载完成后自动执行
  loadLocalJSON()
})

onUnmounted(() => {
  if (renderer) {
    renderer.dispose()
  }
  if (controls) {
    controls.dispose()
  }
  // ✅ 清理自动保存计时器
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    autoSaveTimer = null
  }
  // ✅ 清理自动播放计时器
  if (autoPlayTimer) {
    clearInterval(autoPlayTimer)
    autoPlayTimer = null
  }
})
</script>

<style scoped lang="scss">
.worker-manual-viewer {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
  overflow: hidden;
}

// 零件状态选择弹窗
.part-status-popup {
  position: fixed;
  z-index: 1000;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 320px;
  max-width: 500px;
  transform: translate(-50%, 10px);

  .popup-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #eee;
    gap: 12px;

    .part-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      min-width: 0;
    }

    .part-name {
      font-weight: 600;
      color: #333;
      word-break: break-all;
      line-height: 1.4;
    }

    .part-nauo {
      font-size: 12px;
      color: #888;
      word-break: break-all;
    }
  }

  .popup-content {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;

    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 4px;

      &.gray {
        background: #888888;
      }
      &.yellow {
        background: #ffff00;
        border: 1px solid #ffaa00;
      }
      &.blue {
        background: #4a90e2;
      }
    }
  }

  .popup-footer {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #eee;
    display: flex;
    justify-content: center;
  }
}

// 已删除零件下拉菜单
.deleted-parts-dropdown {
  margin-top: 8px;

  .deleted-part-name {
    margin-right: 8px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

// 草稿模式提示条
.draft-notice-bar {
  background: linear-gradient(90deg, #fff3cd 0%, #ffeeba 100%);
  border-bottom: 2px solid #ffc107;
  padding: 10px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .draft-notice-content {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #856404;
    font-weight: 600;
    font-size: 14px;

    .el-icon {
      font-size: 18px;
    }
  }

  .draft-notice-actions {
    display: flex;
    gap: 12px;
  }
}

// 历史版本只读提示条
.history-notice-bar {
  background: linear-gradient(90deg, #e6f7ff 0%, #bae7ff 100%);
  border-bottom: 2px solid #1890ff;
  padding: 10px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .history-notice-content {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #0050b3;
    font-size: 14px;

    .el-icon {
      font-size: 18px;
    }

    strong {
      font-weight: 700;
      color: #1890ff;
    }
  }

  .history-notice-actions {
    display: flex;
    gap: 12px;
  }
}

.top-bar {
  height: 100px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);

  .product-info {
    min-width: 250px;

    h1 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 700;
    }
  }

  .progress-section {
    flex: 1;

    .progress-info {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;

      .current-step {
        font-size: 32px;
        font-weight: 700;
      }

      .total-steps {
        font-size: 20px;
        opacity: 0.8;
      }

      .step-title {
        font-size: 16px;
        margin-left: 16px;
        opacity: 0.9;
      }
    }
  }

  .top-actions {
    display: flex;
    gap: 8px;
    align-items: center;
    background: rgba(255, 255, 255, 0.95);
    padding: 8px 16px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .action-group {
    display: flex;
    align-items: center;
    gap: 8px;

    :deep(.el-button) {
      border-radius: 8px;
      font-weight: 500;
      min-height: 40px;
      padding: 0 16px;
      border: 1px solid #e4e7ed;
      background: white;
      color: #606266;
      transition: all 0.2s;

      &:hover {
        background: #f5f7fa;
        border-color: #c0c4cc;
        color: #303133;
      }

      &.el-button--primary {
        background: #409eff;
        border-color: #409eff;
        color: white;

        &:hover {
          background: #66b1ff;
          border-color: #66b1ff;
        }
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }

  .nav-group {
    .step-indicator {
      font-size: 14px;
      font-weight: 600;
      color: #606266;
      padding: 0 8px;
      min-width: 60px;
      text-align: center;
    }
  }

  .action-divider {
    width: 1px;
    height: 28px;
    background: #dcdfe6;
    margin: 0 8px;
  }

  .status-group {
    .admin-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 12px;
      background: #f0f9eb;
      color: #67c23a;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;

      .el-icon {
        font-size: 14px;
      }
    }
  }
}

.main-workspace {
  flex: 1;
  min-height: 0;  // ✅ 关键！让 flex 子元素可以收缩，防止溢出
  display: grid;
  grid-template-columns: 300px 1fr 400px;
  grid-template-rows: 1fr;  // ✅ 限制行高度为可用空间
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

.mobile-action-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 8px 16px;

  :deep(.el-button--primary.is-plain) {
    background: #f5f5f5;
    border-color: #dcdcdc;
    color: #111;
    box-shadow: none;
  }
}

.left-sidebar, .right-sidebar {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  min-height: 0;  // ✅ 让 grid 子元素可以收缩
}

.left-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;

  .section-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #333;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .page-indicator {
      font-size: 14px;
      color: #666;
      font-weight: normal;
    }
  }

  .drawing-section-full {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .drawings-container {
      flex: 1;
      height: 100%;
    }

    .drawings-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 8px;
    }

    .drawing-item {
      background: #fafafa;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      overflow: auto;
      cursor: pointer;
      transition: all 0.3s ease;

      &:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
      }

      &.zoomed {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        border-radius: 0;
        border: none;
        background: rgba(0, 0, 0, 0.95);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;

        .drawing-image {
          max-width: 95vw;
          max-height: 95vh;
          width: auto;
          height: auto;
        }
      }

      .drawing-image {
        max-width: 100%;
        width: auto;
        height: auto;
        max-height: 60vh;
        object-fit: contain;
        display: block;
        margin: 0 auto;
        background: white;
        user-select: none;
        -webkit-user-drag: none;
      }

      .drawing-zoom-bar {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 6px 0 8px;

        .scale-text {
          font-size: 12px;
          color: #555;
          min-width: 40px;
          text-align: center;
        }
      }
    }

    .drawing-placeholder {
      width: 100%;
      height: 300px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: #fafafa;
      border: 2px dashed #e5e7eb;
      border-radius: 8px;

      p {
        margin: 0;
        color: #999;
      }
    }
  }

  .drawing-section-old {
    flex: 1;

    .drawing-viewer {
      height: 100%;
      background: #fafafa;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
      position: relative;
      transition: all 0.3s ease;
      user-select: none;

      &.zoomed {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        border-radius: 0;
        background: rgba(0, 0, 0, 0.95);
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .drawing-image {
        width: 100%;
        height: 100%;
        max-height: 80vh;
        object-fit: contain;
        object-fit: contain;
        background: white;
        transition: transform 0.2s ease;
        transform-origin: center center;
        user-select: none;
        -webkit-user-drag: none;
      }

      .drawing-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;

        p {
          margin: 0;
          color: #999;
        }
      }

      .drawing-nav-buttons {
        position: absolute;
        bottom: 16px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 12px;
        z-index: 10;

        :deep(.el-button) {
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(4px);

          &:hover:not(:disabled) {
            background: white;
          }
        }
      }
    }
  }

  .parts-section {
    .parts-list {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .part-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: #f9fafb;
        border-radius: 8px;
        border: 1px solid #e5e7eb;

        .part-icon {
          font-size: 32px;
        }

        .part-details {
          flex: 1;

          .part-name {
            font-weight: 600;
            margin-bottom: 4px;
          }

          .part-code {
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
          }
        }
      }

      .empty-hint {
        text-align: center;
        padding: 24px;
        color: #999;
      }
    }
  }
}

.center-viewer {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  min-height: 0;  // ✅ 允许收缩，防止撑破容器
  overflow: hidden;

  .model-container {
    flex: 1;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);

    canvas {
      display: block;
      width: 100%;
      height: 100%;
    }
  }

  .model-controls {
    padding: 12px 16px;
    border-top: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;

    .controls-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    // PC端：滑块和按钮在同一行
    .explode-slider-inline {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: 8px;

      .slider-value {
        font-size: 13px;
        font-weight: 600;
        color: #7c3aed;
        min-width: 40px;
        text-align: right;
      }
    }

    // 移动端：滑块单独一行
    .explode-slider {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: #f5f7fa;
      border-radius: 8px;
      width: 100%;

      .slider-label {
        font-size: 14px;
        color: #666;
        white-space: nowrap;
      }

      .slider-value {
        font-size: 14px;
        font-weight: 600;
        color: #7c3aed;
        min-width: 45px;
        text-align: right;
      }
    }
  }
}

.right-sidebar {
  padding: 16px;

  .step-detail-card {
    margin-bottom: 16px;

    .step-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
      justify-content: space-between;

      .step-admin-actions {
        display: flex;
        gap: 8px;
      }

      .step-badge {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: 700;
        flex-shrink: 0;
      }

      h2 {
        margin: 0;
        font-size: 20px;
        color: #333;
      }
    }

    .step-content {
      h3 {
        font-size: 16px;
        margin: 16px 0 12px 0;
        color: #333;
      }

      .description-text {
        font-size: 15px;
        line-height: 1.8;
        color: #555;
        margin-bottom: 16px;
      }

      .operation-list {
        padding-left: 20px;
        margin: 0;

        li {
          margin-bottom: 8px;
          line-height: 1.6;
        }
      }

      .tools-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .keypoints-list {
        padding-left: 20px;
        margin: 0;

        li {
          margin-bottom: 8px;
          line-height: 1.6;
          color: #555;
        }
      }

      .time-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #666;
      }
    }
  }

  .quick-reference-tabs {
    .tab-content-scroll {
      max-height: 300px;
      overflow-y: auto;

      .ref-item {
        padding: 12px;
        margin-bottom: 12px;
        background: #f9fafb;
        border-radius: 8px;

        .ref-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        p {
          margin: 4px 0;
          font-size: 14px;
          color: #555;
        }
      }
    }
  }
}

// 编辑Dialog样式
.edit-section {
  max-height: 500px;
  overflow-y: auto;
  padding: 12px;

  .edit-item {
    margin-bottom: 16px;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
  }

  .welding-edit-card,
  .safety-edit-card {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 600;
    }

    :deep(.el-card__body) {
      padding: 16px;
    }

    :deep(.el-divider) {
      margin: 12px 0;
    }

    :deep(.el-form-item) {
      margin-bottom: 12px;
    }
  }
}

.loading-screen {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;

  p {
    font-size: 18px;
    color: #666;
  }
}

.mobile-drawer-body {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .worker-manual-viewer {
    height: auto;
    min-height: 100vh;
    overflow: auto;
  }

  .top-bar {
    height: auto;
    padding: 12px 14px;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;

    .product-info h1 {
      font-size: 16px;
      margin-bottom: 4px;
    }

    .progress-section {
      width: 100%;

      .progress-info {
        .current-step {
          font-size: 22px;
        }

        .total-steps {
          font-size: 16px;
        }

        .step-title {
          font-size: 14px;
          margin-left: 8px;
        }
      }
    }

    .top-actions {
      flex-wrap: wrap;
      width: 100%;
      padding: 8px;
    }

    .action-divider {
      display: none;
    }

    .action-group {
      flex-wrap: wrap;

      :deep(.el-button) {
        min-height: 36px;
        font-size: 13px;
      }
    }
  }

  .main-workspace {
    display: flex;
    flex-direction: column;
    grid-template-columns: none;
    gap: 12px;
    padding: 12px;
    overflow: visible;
  }

  .center-viewer {
    min-height: clamp(320px, 60vh, 520px);

    .model-controls {
      width: 100%;
      align-items: stretch;
      .controls-row {
        justify-content: space-between;
      }
      .el-button-group {
        width: 100%;
        display: flex;
      }
      .explode-slider {
        width: 100%;
        justify-content: space-between;
      }
    }
  }

  .right-sidebar,
  .left-sidebar {
    display: none;
  }
}

// 移动端横屏强化布局：保持 3D 主视区，压缩边距
@media (max-width: 1024px) and (orientation: landscape) {
  .worker-manual-viewer {
    min-height: 100vh;
    overflow: auto;
  }

  .mobile-action-bar {
    position: sticky;
    top: 0;
    justify-content: flex-start;
    padding: 8px 12px;
    gap: 8px;
    z-index: 5;
  }

  .main-workspace {
    padding: 8px 12px;
    gap: 8px;
    overflow: auto;
  }

  .center-viewer {
    min-height: clamp(320px, 70vh, calc(100vh - 180px));
    .model-controls {
      padding: 12px;
      gap: 8px;
      .explode-slider {
        width: 100%;
      }
    }
  }

  .mobile-drawer-body {
    height: calc(100vh - 150px);
    overflow-y: auto;
  }
}

</style>

