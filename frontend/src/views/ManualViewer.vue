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
        <el-button size="small" @click="goEditFromHistory">
          修改当前版本
        </el-button>
      </div>
    </div>

    <!-- 草稿模式提示条 -->
    <div v-if="isAdmin && isDraftMode && !isReadOnlyMode" class="draft-notice-bar">
      <div class="draft-notice-content">
        <el-icon><Warning /></el-icon>
        <span>草稿模式 - 当前修改基于 {{ manualData?.version || '未知版本' }}，您有未发布的修改</span>
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

    <!-- 顶部进度条（图片放大时隐藏） -->
    <div class="top-bar">
      <div class="product-info">
        <h1>{{ productName }}</h1>
        <el-tag v-if="!isMobile" type="info" size="large">装配说明书</el-tag>
      </div>

      <div class="progress-section">
        <div class="progress-info">
          <span class="current-step">步骤 {{ currentStepIndex + 1 }}</span>
          <span class="total-steps">/ {{ totalSteps }}</span>
        <span class="step-title">{{ currentStepDisplayTitle }}</span>
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
                    <el-dropdown-item command="reorderSteps">
                      <el-icon><Sort /></el-icon> 调整步骤顺序
                    </el-dropdown-item>
                    <el-dropdown-item command="deleteStep" divided>
                      <el-icon><Delete /></el-icon> 删除当前步骤
                    </el-dropdown-item>
                    <el-dropdown-item command="deleteManual" divided>
                      <el-icon><Delete /></el-icon> 删除当前图纸
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
                    <el-dropdown-item v-if="showHistoryEntry" command="history">
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
    <div class="main-workspace" :style="mainWorkspaceStyle">
      <!-- 左侧：图纸参考（全屏显示） -->
      <div class="left-sidebar" v-if="!isMobile" :class="{ 'is-collapsed': isLeftSidebarCollapsed }">
        <div class="sidebar-content">
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
                  @click="openImageViewer(index)"
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

        <div class="split-handle split-handle-left" @pointerdown="startSidebarResize('left', $event)"></div>
        <div class="split-toggle left" :title="isLeftSidebarCollapsed ? '展开图纸' : '收起图纸'" @click="toggleLeftSidebar">
          {{ isLeftSidebarCollapsed ? '⟩' : '⟨' }}
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
              :type="disableInstalledStatusOption ? 'default' : (getPartStatus(selectedMesh) === 'installed' ? 'primary' : 'default')"
              :plain="disableInstalledStatusOption"
              :disabled="disableInstalledStatusOption"
              @click="setPartStatus('installed')"
              size="small"
              class="installed-disabled-button"
            >
              <span
                class="status-dot"
                :class="disableInstalledStatusOption ? 'disabled-installed' : 'blue'"
              ></span>
              已装<span v-if="disableInstalledStatusOption" class="disabled-label">（禁用）</span>
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
      <div class="right-sidebar" v-if="!isMobile" :class="{ 'is-collapsed': isRightSidebarCollapsed }">
        <div class="sidebar-content">
          <el-scrollbar height="100%">

          <!-- 当前步骤 -->
          <div class="step-detail-card" v-if="currentStepData">
            <div class="step-header">
              <div class="step-badge">{{ currentStepIndex + 1 }}</div>
              <h2>{{ currentStepDisplayTitle }}</h2>
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

        <div class="split-handle split-handle-right" @pointerdown="startSidebarResize('right', $event)"></div>
        <div class="split-toggle right" :title="isRightSidebarCollapsed ? '展开步骤' : '收起步骤'" @click="toggleRightSidebar">
          {{ isRightSidebarCollapsed ? '⟨' : '⟩' }}
        </div>
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
              @click="openImageViewer(index)"
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
              <h2>{{ currentStepDisplayTitle }}</h2>
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
            <el-option :label="'在开头插入'" :value="INSERT_AT_START" />
            <el-option
              v-for="step in allSteps"
              :key="step.step_id"
              :label="`在步骤${step.step_number}「${getStepDisplayTitle(step)}」之后`"
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

    <!-- 步骤顺序调整 Dialog（管理员） -->
    <el-dialog
      v-model="showStepOrderDialog"
      title="调整步骤顺序"
      width="520px"
      :close-on-click-modal="false"
    >
      <div class="step-order-hint">
        <el-text type="info">
          拖拽左侧“≡”调整顺序；确认后会保存到草稿（未发布前仅管理员可见）。
        </el-text>
      </div>
      <div class="step-order-list">
        <draggable
          v-model="tempStepOrder"
          item-key="step_id"
          handle=".drag-handle"
          animation="200"
          :force-fallback="true"
          :scroll="true"
          :scroll-sensitivity="140"
          :scroll-speed="24"
          :bubble-scroll="true"
          :fallback-on-body="true"
          ghost-class="step-order-ghost"
          chosen-class="step-order-chosen"
        >
          <template #item="{ element, index }">
            <div
              class="step-order-item"
              :class="{ current: element.step_id === currentStepData?.step_id }"
            >
              <span class="drag-handle">≡</span>
              <span class="step-number">{{ index + 1 }}.</span>
              <span class="step-title">{{ getStepDisplayTitle(element) }}</span>
              <el-tag
                v-if="element.step_id === currentStepData?.step_id"
                size="small"
                type="warning"
              >
                当前
              </el-tag>
            </div>
          </template>
        </draggable>
      </div>
      <template #footer>
        <el-button @click="showStepOrderDialog = false">取消</el-button>
        <el-button type="primary" :loading="stepOrderSaving" @click="confirmStepOrder">
          确认调整
        </el-button>
      </template>
    </el-dialog>

    <!-- 内容编辑Dialog -->
  <el-dialog
    v-model="showEditDialog"
    :title="`编辑步骤${currentStepData?.step_number} - ${currentStepDisplayTitle}`"
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
      <el-form-item label="步骤标题">
        <el-input
          v-model="editData.step_title"
          placeholder="例如：安装方形板-机加"
        />
        <el-text type="info" size="small" style="margin-left: 8px;">
          将同步到步骤的 title/action 字段
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
        <el-form-item label="当前线上版本">
          <el-tag type="info">{{ currentOnlineVersion }}</el-tag>
        </el-form-item>
        <el-form-item label="当前修改版本">
          <el-tag :type="isDraftMode ? 'warning' : 'info'">
            {{ draftVersionDisplay || '无草稿' }}
          </el-tag>
        </el-form-item>
        <el-form-item v-if="isReadOnlyMode" label="正在预览">
          <el-tag type="warning">{{ previewVersionDisplay }}</el-tag>
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
            :maxlength="500"
            show-word-limit
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

    <!-- 草稿来源提示 Dialog -->
    <el-dialog
      v-model="draftPromptVisible"
      title="发现草稿"
      width="520px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <p style="margin-bottom: 12px">当前存在一个草稿，基于版本：<strong>{{ draftPromptContext.draftBaseVersion }}</strong></p>
      <p style="margin-bottom: 12px">
        草稿创建时间：<strong>{{ formatDateTime(draftPromptContext.draftCreatedAt) }}</strong>
        <span v-if="draftPromptContext.createdAtFallback">（使用最后保存时间）</span>
      </p>
      <p v-if="draftPromptContext.hasPreview" style="margin-bottom: 12px">
        你刚刚预览了 <strong>{{ draftPromptContext.previewVersion }}</strong>，可选择用该版本创建新草稿。
      </p>
      <p v-else style="margin-bottom: 12px">
        没有历史预览版本，继续当前草稿或丢弃草稿回到最新线上。
      </p>
      <template #footer>
        <div class="draft-dialog-actions">
          <el-button @click="handleContinueDraft">继续修改上一个未发布版本 {{ draftPromptContext.draftBaseVersion }}</el-button>
          <el-button
            type="primary"
            :disabled="!draftPromptContext.hasPreview"
            :loading="draftPromptLoading"
            @click="handleDiscardAndUsePreview"
          >
            丢弃上一个版本 {{ draftPromptContext.draftBaseVersion }}，改当前预览 {{ draftPromptContext.previewVersion || '（无预览）' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>

  <Teleport to="body">
    <ElImageViewer
      v-if="imageViewerVisible"
      :url-list="drawingImages"
      :initial-index="imageViewerIndex"
      hide-on-click-modal
      teleported
      @close="imageViewerVisible = false"
    />
  </Teleport>

  <!-- 移动端原图滚动查看 -->
  <div
    v-if="mobileImagePreviewVisible"
    class="mobile-image-overlay"
    @click.self="closeMobileImagePreview()"
    @touchstart.stop.prevent="handleMobilePreviewTouchStart"
    @touchmove.stop.prevent="handleMobilePreviewTouchMove"
    @touchend.stop.prevent="handleMobilePreviewTouchEnd"
    @touchcancel.stop.prevent="handleMobilePreviewTouchEnd"
  >
    <div class="mobile-image-header">
      <span>图纸预览</span>
      <div class="mobile-image-actions">
        <el-button size="small" @click="resetMobileImageTransform()">重置</el-button>
        <el-button size="small" type="primary" @click="closeMobileImagePreview()">关闭</el-button>
      </div>
    </div>
    <div class="mobile-image-wrapper" ref="mobileImageWrapper">
      <img
        :src="mobileImagePreviewUrl"
        alt="drawing preview"
        :style="{
          transform: `translate(${mobileImageOffset.x}px, ${mobileImageOffset.y}px) scale(${mobileImageScale})`,
          transformOrigin: 'top left'
        }"
        @load="handleMobileImageLoad"
        @click="handleMobileImageTap"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, reactive, type CSSProperties } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Loading, ArrowLeft, ArrowRight, ArrowDown, Picture, Box,
  Refresh, View, Grid, Clock, Lock, Edit, Plus, Upload, Document,
  Warning, Delete, Close, User, VideoPlay, VideoPause, Sort
} from '@element-plus/icons-vue'
import { useMediaQuery } from '@vueuse/core'
import axios from 'axios'
import draggable from 'vuedraggable'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { ElImageViewer } from 'element-plus'

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

interface StepOrderItem {
  step_id: string
  title: string
}

// ✅ 接收路由参数 taskId
const props = defineProps<{
  taskId: string
}>()

const isMobile = useMediaQuery('(max-width: 1024px)')

// ============ 桌面端：左右侧栏拖拽/折叠（方案B） ============
const SIDEBAR_RAIL_WIDTH = 16
const LEFT_SIDEBAR_DEFAULT_WIDTH = 300
const RIGHT_SIDEBAR_DEFAULT_WIDTH = 400
const LEFT_SIDEBAR_MIN_WIDTH = 200
const LEFT_SIDEBAR_MAX_WIDTH = 420
const RIGHT_SIDEBAR_MIN_WIDTH = 280
const RIGHT_SIDEBAR_MAX_WIDTH = 520

const leftSidebarWidth = ref(LEFT_SIDEBAR_DEFAULT_WIDTH)
const rightSidebarWidth = ref(RIGHT_SIDEBAR_DEFAULT_WIDTH)
const lastLeftExpandedWidth = ref(LEFT_SIDEBAR_DEFAULT_WIDTH)
const lastRightExpandedWidth = ref(RIGHT_SIDEBAR_DEFAULT_WIDTH)

const isLeftSidebarCollapsed = computed(() => leftSidebarWidth.value <= SIDEBAR_RAIL_WIDTH)
const isRightSidebarCollapsed = computed(() => rightSidebarWidth.value <= SIDEBAR_RAIL_WIDTH)

const mainWorkspaceStyle = computed<CSSProperties>(() => {
  if (isMobile.value) return {}
  return {
    gridTemplateColumns: `${leftSidebarWidth.value}px 1fr ${rightSidebarWidth.value}px`
  }
})

const clampNumber = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

let sidebarResizeRaf: number | null = null
const schedule3DViewerResize = () => {
  if (sidebarResizeRaf !== null) return
  sidebarResizeRaf = requestAnimationFrame(() => {
    sidebarResizeRaf = null
    // 侧栏宽度变化不会触发 window resize，这里主动重算 3D 画布尺寸
    if (resizeHandler) {
      resizeHandler()
    } else {
      window.dispatchEvent(new Event('resize'))
    }
  })
}

type SidebarSide = 'left' | 'right'
let sidebarDragCleanup: (() => void) | null = null

const startSidebarResize = (side: SidebarSide, event: PointerEvent) => {
  if (isMobile.value) return
  if (event.button !== 0) return

  event.preventDefault()

  const startX = event.clientX
  const startLeftWidth = leftSidebarWidth.value
  const startRightWidth = rightSidebarWidth.value

  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  const handleMove = (moveEvent: PointerEvent) => {
    const dx = moveEvent.clientX - startX
    if (side === 'left') {
      const next = clampNumber(startLeftWidth + dx, LEFT_SIDEBAR_MIN_WIDTH, LEFT_SIDEBAR_MAX_WIDTH)
      leftSidebarWidth.value = next
      if (next > SIDEBAR_RAIL_WIDTH) lastLeftExpandedWidth.value = next
    } else {
      const next = clampNumber(startRightWidth - dx, RIGHT_SIDEBAR_MIN_WIDTH, RIGHT_SIDEBAR_MAX_WIDTH)
      rightSidebarWidth.value = next
      if (next > SIDEBAR_RAIL_WIDTH) lastRightExpandedWidth.value = next
    }
    schedule3DViewerResize()
  }

  const handleUp = () => {
    sidebarDragCleanup?.()
  }

  sidebarDragCleanup = () => {
    window.removeEventListener('pointermove', handleMove)
    window.removeEventListener('pointerup', handleUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    sidebarDragCleanup = null
  }

  try {
    const target = event.currentTarget as HTMLElement | null
    target?.setPointerCapture?.(event.pointerId)
  } catch {
    // ignore
  }

  window.addEventListener('pointermove', handleMove, { passive: true })
  window.addEventListener('pointerup', handleUp, { passive: true })
}

const toggleLeftSidebar = () => {
  if (isLeftSidebarCollapsed.value) {
    leftSidebarWidth.value = clampNumber(
      lastLeftExpandedWidth.value || LEFT_SIDEBAR_DEFAULT_WIDTH,
      LEFT_SIDEBAR_MIN_WIDTH,
      LEFT_SIDEBAR_MAX_WIDTH
    )
  } else {
    lastLeftExpandedWidth.value = leftSidebarWidth.value
    leftSidebarWidth.value = SIDEBAR_RAIL_WIDTH
  }
  schedule3DViewerResize()
}

const toggleRightSidebar = () => {
  if (isRightSidebarCollapsed.value) {
    rightSidebarWidth.value = clampNumber(
      lastRightExpandedWidth.value || RIGHT_SIDEBAR_DEFAULT_WIDTH,
      RIGHT_SIDEBAR_MIN_WIDTH,
      RIGHT_SIDEBAR_MAX_WIDTH
    )
  } else {
    lastRightExpandedWidth.value = rightSidebarWidth.value
    rightSidebarWidth.value = SIDEBAR_RAIL_WIDTH
  }
  schedule3DViewerResize()
}

const showDrawingsDrawer = ref(false)
const showDetailsDrawer = ref(false)
let viewerInitAttempts = 0
const lastPreviewKey = computed(() => `last_preview_version_${props.taskId}`)
const draftPromptSuppressKey = computed(() => `draft_prompt_suppress_once_${props.taskId}`)
const creatingPreviewDraft = ref(false)
const imageViewerVisible = ref(false)
const imageViewerIndex = ref(0)
let prevDocTouchAction = ''
let prevBodyTouchAction = ''
const mobileImagePreviewVisible = ref(false)
const mobileImagePreviewUrl = ref('')
const mobileImageScale = ref(1)
const mobileImageOffset = reactive({ x: 0, y: 0 })
const mobileImageNaturalSize = reactive({ w: 0, h: 0 })
const mobileImageWrapper = ref<HTMLElement | null>(null)
const tapStart = reactive({ x: 0, y: 0, t: 0 })
const overlayStack: Array<'image' | 'drawer'> = []
let closingOverlayFromManual = false
let closingOverlayFromPopstate = false
const mobileDragState = reactive({
  isDragging: false,
  startX: 0,
  startY: 0,
  startOffsetX: 0,
  startOffsetY: 0
})
const mobilePinchState = reactive({
  isPinching: false,
  startDistance: 0,
  startScale: 1
})

const router = useRouter()
const route = useRoute()

// 历史版本只读模式（通过 ?version=v2 参数触发）
const historyVersion = computed(() => route.query.version as string | undefined)
const isReadOnlyMode = computed(() => !!historyVersion.value)
const entrySource = computed(() => {
  const source = route.query.source
  return Array.isArray(source) ? source[0] : source
})

const manualData = ref<any>(null)
// ✅ 存储 step3_glb_inventory.json 的 node_to_geometry 数据（用于显示3D零件实际名称）
const glbNodeToGeometry = ref<{ node: string; geometry: string }[]>([])
const latestVersion = ref<string | null>(null)
let suppressDraftPromptOnce = false
const editingFromHistory = ref(false)
const showHistoryEntry = computed(() => entrySource.value === 'viewer' && !editingFromHistory.value)

// 版本号只允许向上更新，避免历史/草稿覆盖最新版本
const parseVersionNumber = (ver?: string | null): number | null => {
  if (!ver) return null
  const match = String(ver).match(/(\d+)/)
  if (!match) return null
  const num = parseInt(match[1], 10)
  return Number.isNaN(num) ? null : num
}

const updateLatestVersion = (candidate?: string | null) => {
  if (!candidate) return
  const candidateNum = parseVersionNumber(candidate)
  if (candidateNum === null) return
  const currentNum = parseVersionNumber(latestVersion.value)
  if (currentNum === null || candidateNum > currentNum) {
    latestVersion.value = candidate
  }
}

const setManualDataValue = (data: any) => {
  manualData.value = data
  if (manualData.value && manualData.value._edit_version === undefined) {
    manualData.value._edit_version = 0
  }
  updateLatestVersion(data?.version)

  // ✅ 从 part_assembly_states 恢复零件状态到内存 Map
  restorePartAssemblyStates(data)
}

// 获取后端当前最新版本号（用于历史版本预览时正确显示即将发布版本）
const fetchLatestVersion = async () => {
  try {
    const resp = await axios.head(`/api/manual/${props.taskId}/version`)
    const serverVersion = resp.headers['x-manual-version']
    updateLatestVersion(serverVersion as string)
  } catch (error) {
    console.warn('获取最新版本号失败，使用已加载版本', error)
  }
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
const draftPromptVisible = ref(false)
const draftPromptLoading = ref(false)
const draftPromptContext = reactive({
  draftBaseVersion: '',
  previewVersion: '',
  hasPreview: false,
  draftCreatedAt: '',
  createdAtFallback: false
})

const currentOnlineVersion = computed(() => {
  return latestVersion.value || manualData.value?.version || '未发布'
})
const previewVersionDisplay = computed(() => {
  return manualData.value?.version || '未发布'
})
const formatDateTime = (value?: string) => {
  if (!value) return '未知'
  try {
    const date = new Date(value)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch {
    return value || '未知'
  }
}
const draftVersionDisplay = computed(() => {
  if (!isDraftMode.value) return ''
  const base = manualData.value?.version || currentOnlineVersion.value || '未发布'
  return `${base}（草稿）`
})

const nextVersionPreview = computed(() => {
  const raw = latestVersion.value || manualData.value?.version || 'v0'
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
const showStepOrderDialog = ref(false)
const stepOrderSaving = ref(false)
const tempStepOrder = ref<StepOrderItem[]>([])
const publishForm = ref({ changelog: '' })
const publishing = ref(false)
const editActiveTab = ref('welding')
const saving = ref(false)
const componentNameInput = ref('')
const showInsertDialog = ref(false)
const INSERT_AT_START = '__START__'
const insertAfterStepId = ref<string>(INSERT_AT_START)
const insertAction = ref('')
const insertDescription = ref('')
const inserting = ref(false)
const deletingStep = ref(false)
const deletingManual = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

// 编辑数据（使用新的类型定义）
const editData = ref({
  welding_requirements: [] as WeldingRequirementEdit[],
  safety_warnings: [] as SafetyWarningEdit[],
  quality_check: '' as string,
  step_title: '' as string,
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
let gridBoundary: THREE.Line | null = null
let animationId: number | null = null
let resizeHandler: (() => void) | null = null

// 固定网格配置：与验证脚本一致，提供小范围且有边界的网格
const GRID_SIZE = 150
const GRID_DIVISIONS = 40
const GRID_HEIGHT = -5
const GRID_COLOR_CENTER = 0x666666
const GRID_COLOR_LINE = 0x999999
const GRID_BOUNDARY_COLOR = 0x444444

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
// ✅ 启用“已装”手动标记，便于手动校准装配状态
const disableInstalledStatusOption = ref(false)

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
const zoomedDrawingIndex = ref<number | null>(null) // 兼容旧逻辑占位

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

const getStepDisplayTitle = (step: any): string => {
  return step?.title || step?.action || '未命名'
}

const currentStepData = computed(() => {
  const stepData = allSteps.value[currentStepIndex.value]

  // 调试：查看步骤数据中是否有图纸字段
  if (stepData) {
    console.log(`📋 步骤${currentStepIndex.value + 1}的数据:`, stepData)
    console.log(`🎨 步骤${currentStepIndex.value + 1}的字段:`, Object.keys(stepData))
  }

  return stepData
})

const currentStepDisplayTitle = computed(() => {
  return getStepDisplayTitle(currentStepData.value)
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

// 图纸缩放控制（移动端默认缩小）
const drawingScales = ref<Record<number, number>>({})
const getDrawingScale = (index: number) => {
  const defaultScale = isMobile.value ? 0.9 : 1
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
  drawingScales.value = { ...drawingScales.value, [index]: isMobile.value ? 0.9 : 1 }
}

// 图纸查看器（Element Plus）
const resetMobileImageTransform = () => {
  mobileImageScale.value = 1
  mobileImageOffset.x = 0
  mobileImageOffset.y = 0
}

const handleMobileImageLoad = (event: Event) => {
  const img = event.target as HTMLImageElement
  if (!img) return
  mobileImageNaturalSize.w = img.naturalWidth
  mobileImageNaturalSize.h = img.naturalHeight
  const wrapper = mobileImageWrapper.value
  if (!wrapper) return
  const fitScaleW = wrapper.clientWidth / (img.naturalWidth || 1)
  const fitScaleH = wrapper.clientHeight / (img.naturalHeight || 1)
  const fitScale = Math.min(1, Math.min(fitScaleW, fitScaleH) * 0.98)
  const scale = fitScale > 0 ? fitScale : 1
  mobileImageScale.value = scale
  const imgW = (img.naturalWidth || 0) * scale
  const imgH = (img.naturalHeight || 0) * scale
  mobileImageOffset.x = (wrapper.clientWidth - imgW) / 2
  mobileImageOffset.y = (wrapper.clientHeight - imgH) / 2
}

const openImageViewer = (index: number) => {
  const targetUrl = drawingImages.value[index]
  if (!targetUrl) return

  if (isMobile.value) {
    mobileImagePreviewUrl.value = targetUrl
    mobileImagePreviewVisible.value = true
    resetMobileImageTransform()
    // 为移动预览插入一层历史，用于拦截物理返回先关闭预览
    if (typeof window !== 'undefined') {
      try {
        window.history.pushState({ overlay: 'mobileImage' }, '', window.location.href)
        overlayStack.push('image')
      } catch (err) {
        console.warn('⚠️ pushState 失败，移动预览返回行为可能无法拦截:', err)
      }
    }
    return
  }

  imageViewerIndex.value = index
  imageViewerVisible.value = true
}

const restoreTouchAction = () => {
  if (typeof document === 'undefined') return
  document.documentElement.style.touchAction = prevDocTouchAction
  document.body.style.touchAction = prevBodyTouchAction
}

watch(imageViewerVisible, (visible) => {
  if (typeof document === 'undefined') return
  if (visible) {
    prevDocTouchAction = document.documentElement.style.touchAction
    prevBodyTouchAction = document.body.style.touchAction
    document.documentElement.style.touchAction = 'none'
    document.body.style.touchAction = 'none'
  } else {
    restoreTouchAction()
  }
})

const getTouchDistance = (event: TouchEvent) => {
  const [t1, t2] = [event.touches[0], event.touches[1]]
  const dx = t1.clientX - t2.clientX
  const dy = t1.clientY - t2.clientY
  return Math.hypot(dx, dy)
}

const handleMobilePreviewTouchStart = (event: TouchEvent) => {
  tapStart.t = Date.now()
  if (event.touches.length === 2) {
    mobilePinchState.isPinching = true
    mobilePinchState.startDistance = getTouchDistance(event)
    mobilePinchState.startScale = mobileImageScale.value
  } else if (event.touches.length === 1) {
    // 初始认为未拖拽，移动时超过阈值再标记
    mobileDragState.isDragging = false
    mobileDragState.startX = event.touches[0].clientX
    mobileDragState.startY = event.touches[0].clientY
    mobileDragState.startOffsetX = mobileImageOffset.x
    mobileDragState.startOffsetY = mobileImageOffset.y
    tapStart.x = event.touches[0].clientX
    tapStart.y = event.touches[0].clientY
  }
}

const handleMobilePreviewTouchMove = (event: TouchEvent) => {
  if (mobilePinchState.isPinching && event.touches.length === 2) {
    event.preventDefault()
    const currentDistance = getTouchDistance(event)
    const ratio = currentDistance / (mobilePinchState.startDistance || 1)
    const nextScale = Math.min(3, Math.max(0.2, mobilePinchState.startScale * ratio))
    mobileImageScale.value = nextScale
    return
  }

  if (mobileDragState.isDragging && event.touches.length === 1) {
    event.preventDefault()
    const dx = event.touches[0].clientX - mobileDragState.startX
    const dy = event.touches[0].clientY - mobileDragState.startY
    mobileImageOffset.x = mobileDragState.startOffsetX + dx
    mobileImageOffset.y = mobileDragState.startOffsetY + dy
  } else if (event.touches.length === 1) {
    // 判断是否达到拖拽阈值（避免轻点被误判为拖拽）
    const dx = event.touches[0].clientX - mobileDragState.startX
    const dy = event.touches[0].clientY - mobileDragState.startY
    if (Math.hypot(dx, dy) > 8) {
      mobileDragState.isDragging = true
    }
  }
}

const handleMobilePreviewTouchEnd = (event: TouchEvent) => {
  const touch = event.changedTouches?.[0]
  const dx = touch ? touch.clientX - tapStart.x : 0
  const dy = touch ? touch.clientY - tapStart.y : 0
  const duration = Date.now() - tapStart.t

  // 在状态复位前判定是否为轻点（无拖拽/捏合）
  const isTap =
    !mobilePinchState.isPinching &&
    Math.hypot(dx, dy) < 8 &&
    duration < 250 &&
    !mobileDragState.isDragging

  mobilePinchState.isPinching = false
  mobileDragState.isDragging = false

  if (isTap) {
    closeMobileImagePreview()
  }
}

// 单击图片时关闭预览（仅当未拖拽/捏合时）
const handleMobileImageTap = () => {
  if (mobilePinchState.isPinching || mobileDragState.isDragging) return
  closeMobileImagePreview()
}

const closeMobileImagePreview = () => {
  mobileImagePreviewVisible.value = false
  resetMobileImageTransform()
  mobileImageNaturalSize.w = 0
  mobileImageNaturalSize.h = 0
  if (overlayStack.length > 0 && overlayStack[overlayStack.length - 1] === 'image' && typeof window !== 'undefined') {
    // 手动关闭时只消费自身的历史层
    try {
      closingOverlayFromManual = true
      overlayStack.pop()
      window.history.back()
    } catch (err) {
      console.warn('⚠️ 关闭预览回退历史失败:', err)
    }
    // 异步重置标记，避免 popstate 将抽屉一起关闭
    setTimeout(() => { closingOverlayFromManual = false }, 0)
  }
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
    const currentTitle = currentStep.title || currentStep.action || ''

    // 🔧 记住原始步骤号（兼容性）
    originalStepNumber.value = currentStepNumber
    componentNameInput.value = currentComponentName || ''
    editData.value.step_title = currentTitle

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
    const newTitle = (editData.value.step_title || '').trim()

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
              if (newTitle) {
                step.title = newTitle
                step.action = newTitle
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
          if (newTitle) {
            step.title = newTitle
            step.action = newTitle
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
        updateLatestVersion(data?.version)
        console.log('✅ 管理员模式：从草稿加载数据')
        await fetchLatestVersion()

        const createdAt = data?.draftCreatedAt
        draftPromptContext.draftCreatedAt = createdAt || data?.lastUpdated || ''
        draftPromptContext.createdAtFallback = !createdAt && !!data?.lastUpdated
        applyDraftPromptSuppressOnce()
        if (!suppressDraftPromptOnce) {
          // 弹出草稿提示，提醒当前草稿基线，并提供选择
          const previewVer = historyVersion.value || getLastPreviewVersion()
          draftPromptContext.draftBaseVersion = data?.version || '未知版本'
          draftPromptContext.previewVersion = previewVer
          draftPromptContext.hasPreview = !!previewVer
          draftPromptVisible.value = true
        } else {
          suppressDraftPromptOnce = false
        }
      } catch (e) {
        // 草稿不存在，fallback 到已发布版本
        const resp = await axios.get(`/api/manual/${props.taskId}`)
        data = resp.data
        isDraftMode.value = false  // 非草稿模式
        updateLatestVersion(data?.version)
        console.log('✅ 管理员模式：草稿不存在，从已发布版本加载')
      }
    } else {
      // 普通用户：只获取已发布版本
      const resp = await axios.get(`/api/manual/${props.taskId}`)
      data = resp.data
      updateLatestVersion(data?.version)
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
  insertAfterStepId.value = currentStepData.value?.step_id || INSERT_AT_START
  insertAction.value = ''
  insertDescription.value = ''
  showInsertDialog.value = true
}

const handleInsertStep = async () => {
  if (!currentStepData.value) {
    ElMessage.error('当前步骤数据不存在')
    return
  }
  if (!insertAction.value.trim()) {
    ElMessage.warning('步骤标题必填')
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
    after_step_id: insertAfterStepId.value === INSERT_AT_START ? null : insertAfterStepId.value,
    new_step: {
      action: insertAction.value.trim(),
      title: insertAction.value.trim(),
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
    suppressDraftPromptOnce = true
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
      `确定删除步骤${currentStepData.value.step_number}「${getStepDisplayTitle(currentStepData.value)}」吗？`,
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
    suppressDraftPromptOnce = true
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

const confirmDeleteManual = async () => {
  if (!isAdmin.value) {
    ElMessage.warning('请先登录管理员')
    return
  }
  try {
    await ElMessageBox.confirm(
      '确定删除当前图纸及其所有版本吗？此操作不可恢复。',
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await handleDeleteManual()
  } catch (error) {
    // 用户取消
  }
}

const handleDeleteManual = async () => {
  if (!props.taskId) {
    ElMessage.error('任务ID不存在')
    return
  }
  try {
    deletingManual.value = true
    await axios.delete(`/api/manual/${props.taskId}`)
    ElMessage.success({ message: '图纸已删除', duration: 1200 })
    // 清理本地缓存
    localStorage.removeItem(`current_manual_${props.taskId}`)
    localStorage.removeItem(`current_manual_draft_${props.taskId}`)
    // 跳转到首页
    router.push('/')
  } catch (error: any) {
    console.error('❌ 删除图纸失败:', error)
    ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    deletingManual.value = false
  }
}

const translatePublishError = (detail: any) => {
  const message = String(detail || '未知错误')
  const lower = message.toLowerCase()
  if (lower.includes('no changes') || lower.includes('nothing to publish') || lower.includes('no modified')) {
    return '未进行修改，无法生成新版本'
  }
  if ((lower.includes('draft') && lower.includes('not found')) || lower.includes('save draft first')) {
    return '草稿不存在，请先保存草稿后再发布'
  }
  return message
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
    updateLatestVersion(response.data.version)
    showPublishDialog.value = false
    publishForm.value.changelog = ''
    isDraftMode.value = false  // 发布后退出草稿模式
    localStorage.removeItem(`current_manual_draft_${props.taskId}`)
    await refreshManualFromServer()
    await init3DViewerAndModel()
  } catch (error: any) {
    console.error('❌ 发布失败', error)
    const detail = error.response?.data?.detail || error.message
    ElMessage.error('发布失败: ' + translatePublishError(detail))
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

// 从历史预览跳回当前版本编辑，自动基于预览版生成草稿
const goEditFromHistory = async () => {
  const previewVer = historyVersion.value || getLastPreviewVersion()
  rememberHistoryPreview()
  editingFromHistory.value = true

  // 没有预览版本时，按原逻辑直接跳回
  if (!previewVer) {
    router.push(`/manual/${props.taskId}`)
    return
  }

  creatingPreviewDraft.value = true
  try {
    const result = await createDraftFromPreviewVersion(previewVer)
    if (result === 'created') {
      ElMessage.success(`已基于 ${previewVer} 创建草稿，正在进入编辑`)
    } else if (result === 'exists') {
      ElMessage.info('已存在草稿，直接进入编辑')
    }
    router.push(`/manual/${props.taskId}`)
  } catch (error: any) {
    console.error('❌ 基于预览创建草稿失败:', error)
    ElMessage.error('创建草稿失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    creatingPreviewDraft.value = false
  }
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
    case 'reorderSteps':
      openStepOrderDialog()
      break
    case 'deleteStep':
      confirmDeleteCurrentStep()
      break
    case 'deleteManual':
      confirmDeleteManual()
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

const getStepOrderDisplayTitle = (step: any): string => {
  const baseTitle = step?.title || step?.action || '未命名步骤'
  if (step?.chapter_type === 'product_assembly') {
    return `【产品】${baseTitle}`
  }
  const comp = step?.component_name || step?.component_code || '组件'
  return `【${comp}】${baseTitle}`
}

const openStepOrderDialog = () => {
  if (!isAdmin.value) {
    ElMessage.warning('请先登录管理员')
    return
  }
  if (isReadOnlyMode.value) {
    ElMessage.warning('历史版本为只读，无法调整步骤顺序')
    return
  }
  if (!allSteps.value.length) {
    ElMessage.warning('暂无步骤，无法调整顺序')
    return
  }
  showStepOrderDialog.value = true
}

watch(showStepOrderDialog, (visible) => {
  if (!visible) return
  // ✅ 每次打开弹窗都用当前的全局顺序生成一个可拖拽副本
  tempStepOrder.value = allSteps.value.map((step: any) => ({
    step_id: step.step_id,
    title: getStepOrderDisplayTitle(step)
  }))
})

const confirmStepOrder = async () => {
  if (stepOrderSaving.value) return

  // 只读/非管理员模式下禁止修改
  if (isReadOnlyMode.value) {
    ElMessage.warning('历史版本为只读，无法调整步骤顺序')
    return
  }
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可调整步骤顺序')
    return
  }
  if (!manualData.value) {
    ElMessage.error('手册数据未加载完成，无法调整步骤顺序')
    return
  }

  // ✅ 基于 step_id 的全局顺序重排：display_order 采用 1000 步进，避免破坏后端插入算法
  const currentStepId = currentStepData.value?.step_id || null
  const expectedCount = allSteps.value.length
  const ordered = tempStepOrder.value || []
  if (!ordered.length || ordered.length !== expectedCount) {
    ElMessage.error('步骤列表数量异常，请刷新后重试')
    return
  }

  const uniqueIds = new Set<string>()
  for (const item of ordered) {
    if (!item?.step_id) continue
    if (uniqueIds.has(item.step_id)) {
      ElMessage.error('检测到重复的 step_id，请刷新后重试')
      return
    }
    uniqueIds.add(item.step_id)
  }
  if (uniqueIds.size !== expectedCount) {
    ElMessage.error('步骤ID不完整，请刷新后重试')
    return
  }

  const orderMap = new Map<string, number>()
  ordered.forEach((item, idx) => {
    orderMap.set(item.step_id, (idx + 1) * 1000)
  })

  // 深拷贝：避免保存失败时污染本地状态
  const updatedData = JSON.parse(JSON.stringify(manualData.value))
  const applied = new Set<string>()

  const applyToSteps = (steps: any[]) => {
    if (!Array.isArray(steps)) return
    for (const step of steps) {
      const stepId = step?.step_id
      if (!stepId) continue
      const newOrder = orderMap.get(stepId)
      if (typeof newOrder === 'number') {
        step.display_order = newOrder
        applied.add(stepId)
      }
    }
    // 写回后对章节内步骤排序，保持 JSON 稳定
    steps.sort((a: any, b: any) => (a?.display_order ?? 0) - (b?.display_order ?? 0))
  }

  if (Array.isArray(updatedData.component_assembly)) {
    for (const chapter of updatedData.component_assembly) {
      applyToSteps(chapter?.steps)
    }
  }
  if (updatedData.product_assembly && Array.isArray(updatedData.product_assembly.steps)) {
    applyToSteps(updatedData.product_assembly.steps)
  }

  const missing = Array.from(orderMap.keys()).filter(id => !applied.has(id))
  if (missing.length > 0) {
    console.error('❌ 步骤重排失败：存在未写回的 step_id', missing)
    ElMessage.error('步骤重排失败：步骤数据不完整，请刷新后重试')
    return
  }

  const currentEditVersion = manualData.value?._edit_version ?? 0
  updatedData._edit_version = currentEditVersion

  try {
    stepOrderSaving.value = true
    const resp = await axios.post(`/api/manual/${props.taskId}/save-draft`, {
      manual_data: updatedData
    })

    if (!resp.data?.success) {
      throw new Error(resp.data?.message || '保存草稿失败')
    }

    updatedData._edit_version = currentEditVersion + 1
    if (resp.data?.lastUpdated) {
      updatedData.lastUpdated = resp.data.lastUpdated
    }
    setManualDataValue(updatedData)

    // ✅ 立即显示草稿提示条
    isDraftMode.value = true

    // 更新缓存（草稿）
    const cacheDraftKey = `current_manual_draft_${props.taskId}`
    localStorage.setItem(cacheDraftKey, JSON.stringify(updatedData))

    showStepOrderDialog.value = false
    ElMessage.success('步骤顺序已保存到草稿')

    // ✅ 重新定位到原来正在查看的步骤（按 step_id，而不是旧 index）
    await nextTick()
    if (currentStepId) {
      const newIndex = allSteps.value.findIndex(s => s.step_id === currentStepId)
      if (newIndex >= 0) {
        currentStepIndex.value = newIndex
      }
    }

    // ✅ 强制刷新3D显示，避免“顺序变了但 currentStepIndex 未变化”导致的显示不同步
    updateStepDisplay(true)
  } catch (error: any) {
    console.error('❌ 保存步骤顺序失败:', error)
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    stepOrderSaving.value = false
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

    // ✅ 丢弃草稿后强制恢复零件可见性
    restoreAllPartsVisibility()

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
        rememberHistoryPreview()
        await fetchLatestVersion()
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
        await fetchLatestVersion()
        const createdAt = draftResp.data?.draftCreatedAt
        draftPromptContext.draftCreatedAt = createdAt || draftResp.data?.lastUpdated || ''
        draftPromptContext.createdAtFallback = !createdAt && !!draftResp.data?.lastUpdated
        applyDraftPromptSuppressOnce()
        if (!suppressDraftPromptOnce) {
          const previewVer = historyVersion.value || getLastPreviewVersion()
          draftPromptContext.draftBaseVersion = draftResp.data?.version || '未知版本'
          draftPromptContext.previewVersion = previewVer
          draftPromptContext.hasPreview = !!previewVer
          draftPromptVisible.value = true
        } else {
          suppressDraftPromptOnce = false
        }
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
        updateLatestVersion(serverVersion as string)
        updateLatestVersion(cached.version)

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
        updateLatestVersion(cached.version)
        console.log('✅ 从缓存加载说明书成功 (版本检查失败):', manualData.value)
        ElMessage.success('装配说明书加载成功！')
        await init3DViewerAndModel()
        return
      }
    }

    // 版本不一致或无缓存，从后端 API 获取已发布版本
    const response = await axios.get(`/api/manual/${props.taskId}`)
    setManualDataValue(response.data)
    updateLatestVersion(response.data?.version)

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

// 路由中的 historyVersion 变化时重新加载，避免停留在旧版本数据
watch(historyVersion, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    loadLocalJSON()
  }
})

// ============ 草稿提示与操作 ============

const handleContinueDraft = () => {
  draftPromptVisible.value = false
  suppressDraftPromptOnce = true
}

const handleDiscardAndUsePreview = async () => {
  if (!draftPromptContext.hasPreview || !draftPromptContext.previewVersion) {
    ElMessage.warning('当前无预览版本可用，无法切换')
    return
  }
  try {
    draftPromptLoading.value = true
    editingFromHistory.value = true
    // 丢弃当前未发布修改
    await axios.delete(`/api/manual/${props.taskId}/draft`)
    // 拉取预览版本数据
    const resp = await axios.get(`/api/manual/${props.taskId}/version/${draftPromptContext.previewVersion}`)
    const versionData = resp.data
    // 保存为新的未发布修改
    await axios.post(`/api/manual/${props.taskId}/save-draft`, {
      manual_data: {
        ...versionData,
        _edit_version: versionData?._edit_version ?? 0
      }
    })
    ElMessage.success(`已切换为预览版本 ${draftPromptContext.previewVersion} 的修改`)
    draftPromptVisible.value = false
    isDraftMode.value = true
    suppressDraftPromptOnce = true
    clearLastPreviewVersion()
    await refreshManualFromServer()
  } catch (error: any) {
    console.error('❌ 切换到预览版本失败:', error)
    ElMessage.error('切换失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    draftPromptLoading.value = false
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
  }, 3000) // 3秒间隔
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

// 根据模型尺寸自适应缩放，避免极端放大导致视锥体精度问题
const computeAdaptiveScale = (maxDimOriginal: number) => {
  if (!isFinite(maxDimOriginal) || maxDimOriginal <= 0) return 1
  const targetSize = 1500 // 希望模型最大边落在可视范围的目标尺寸
  const maxScale = 10000  // 上限，避免 100 万倍级别放大
  const scale = targetSize / maxDimOriginal
  return Math.min(maxScale, Math.max(1, scale))
}

// 依据固定配置刷新网格：小范围 + 边界，高度锁定
const refreshGridHelper = (_box: THREE.Box3) => {
  if (!scene) return

  if (gridHelper && scene) {
    scene.remove(gridHelper)
  }
  if (gridBoundary && scene) {
    scene.remove(gridBoundary)
  }

  gridHelper = new THREE.GridHelper(GRID_SIZE, GRID_DIVISIONS, GRID_COLOR_CENTER, GRID_COLOR_LINE)
  gridHelper.name = 'manual_grid_helper'
  gridHelper.position.y = GRID_HEIGHT

  const mats = Array.isArray(gridHelper.material) ? gridHelper.material : [gridHelper.material]
  mats.forEach((mat: any) => {
    mat.depthWrite = false
    mat.depthTest = true
    mat.transparent = true
    mat.opacity = 0.35
  })
  gridHelper.renderOrder = -1

  scene.add(gridHelper)

  // 添加边界线，强化范围感知
  const half = GRID_SIZE / 2
  const boundaryY = GRID_HEIGHT + 0.01
  const points = [
    new THREE.Vector3(-half, boundaryY, -half),
    new THREE.Vector3(half, boundaryY, -half),
    new THREE.Vector3(half, boundaryY, half),
    new THREE.Vector3(-half, boundaryY, half),
    new THREE.Vector3(-half, boundaryY, -half)
  ]
  const boundaryMaterial = new THREE.LineBasicMaterial({
    color: GRID_BOUNDARY_COLOR,
    transparent: true,
    opacity: 0.9
  })
  gridBoundary = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), boundaryMaterial)
  gridBoundary.name = 'manual_grid_boundary'
  gridBoundary.renderOrder = -1
  scene.add(gridBoundary)
}

// 基于包围盒重置相机位置/near/far，并更新控制器 target
const fitCameraToBox = (box: THREE.Box3) => {
  if (!camera) return

  const size = new THREE.Vector3()
  box.getSize(size)
  const center = box.getCenter(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z, 1)
  const dist = maxDim * 2.5

  camera.position.set(center.x + dist, center.y + dist * 0.6, center.z + dist)
  camera.lookAt(center)
  camera.near = Math.max(0.1, maxDim / 500)
  camera.far = Math.max(dist * 4, maxDim * 10)
  camera.updateProjectionMatrix()

  if (controls) {
    controls.target.copy(center)
    controls.update()
  }

  console.log('🎯 相机自适应完成', {
    size: size.toArray(),
    center: center.toArray(),
    cameraPosition: camera.position.toArray(),
    near: camera.near,
    far: camera.far
  })
}

// 清理3D资源，避免重复初始化叠加canvas/事件
const cleanup3DViewer = () => {
  if (animationId !== null) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    resizeHandler = null
  }
  if (controls) {
    controls.dispose()
    controls = null
  }
  if (renderer) {
    const dom = renderer.domElement
    if (dom?.parentElement) {
      dom.parentElement.removeChild(dom)
    }
    renderer.dispose()
    renderer = null
  }
  if (scene && gridHelper) {
    scene.remove(gridHelper)
  }
  if (scene && gridBoundary) {
    scene.remove(gridBoundary)
  }
  gridHelper = null
  gridBoundary = null
  model = null
  scene = null
  camera = null
  raycaster = null
  hoverOutlineGroup = null
  hoveredMesh.value = null
  selectedMesh.value = null
  meshOriginalPositions = new Map()
  meshOriginalMaterials = new Map()
  meshExplodeDirections = new Map()
  meshWorldOriginalPositions = new Map()
  meshWorldExplodeDirections = new Map()
}

// 历史预览版本的暂存（用于返回当前页面时创建草稿）
const rememberHistoryPreview = () => {
  if (historyVersion.value) {
    sessionStorage.setItem(lastPreviewKey.value, historyVersion.value)
  }
}

const getLastPreviewVersion = () => {
  return sessionStorage.getItem(lastPreviewKey.value) || ''
}

const clearLastPreviewVersion = () => {
  sessionStorage.removeItem(lastPreviewKey.value)
}

const setDraftPromptSuppressOnce = () => {
  if (typeof window === 'undefined') return
  sessionStorage.setItem(draftPromptSuppressKey.value, '1')
}

const consumeDraftPromptSuppressOnce = (): boolean => {
  if (typeof window === 'undefined') return false
  const hit = sessionStorage.getItem(draftPromptSuppressKey.value)
  if (!hit) return false
  sessionStorage.removeItem(draftPromptSuppressKey.value)
  return true
}

const applyDraftPromptSuppressOnce = () => {
  if (suppressDraftPromptOnce) return
  if (consumeDraftPromptSuppressOnce()) {
    suppressDraftPromptOnce = true
  }
}

// 基于指定预览版本创建草稿；若草稿已存在则直接返回 exists
const createDraftFromPreviewVersion = async (previewVersion: string): Promise<'created' | 'exists'> => {
  try {
    await axios.get(`/api/manual/${props.taskId}/draft`)
    return 'exists'
  } catch (e: any) {
    // 404 表示不存在草稿，可以创建；其他错误抛出
    if (e?.response?.status && e.response.status !== 404) {
      throw e
    }
  }

  const resp = await axios.get(`/api/manual/${props.taskId}/version/${previewVersion}`)
  const versionData = resp.data

  await axios.post(`/api/manual/${props.taskId}/save-draft`, {
    manual_data: {
      ...versionData,
      _edit_version: versionData?._edit_version ?? 0
    }
  })

  setDraftPromptSuppressOnce()
  suppressDraftPromptOnce = true
  clearLastPreviewVersion()
  isDraftMode.value = true
  return 'created'
}

// 如果 sessionStorage 有预览版本且当前没有草稿，自动将预览版转为草稿
const ensurePreviewDraftFromCache = async () => {
  const previewVer = getLastPreviewVersion()
  if (!previewVer) return

  try {
    editingFromHistory.value = true
    const result = await createDraftFromPreviewVersion(previewVer)
    if (result === 'created') {
      ElMessage.success(`已基于预览版本 ${previewVer} 创建草稿`)
    }
  } catch (error: any) {
    console.warn('⚠️ 基于预览版本创建草稿失败，后续将加载线上版本:', error)
  }
}

const init3DViewer = () => {
  console.log('🎬 开始初始化3D查看器...')

  // 先清理旧的实例，避免多次初始化叠加canvas/事件
  cleanup3DViewer()

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

  // 图纸查看器关闭后恢复滚动（兼容旧逻辑的类名移除）
  document.body.classList.remove('manual-viewer-zoomed')

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

  // 添加底部地面网格（初始位置，后续模型加载时仍会重建）
  refreshGridHelper(new THREE.Box3())

  // 动画循环
  const animate = () => {
    animationId = requestAnimationFrame(animate)
    if (controls) controls.update()
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()
  console.log('🎬 动画循环已启动')

  // ✅ 调试：暴露到window对象
  ;(window as any).__three_debug__ = { scene, camera, renderer, controls, THREE }

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
  resizeHandler = handleResize
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

    const maxDimOriginal = Math.max(size.x, size.y, size.z)
    const scaleFactor = computeAdaptiveScale(maxDimOriginal)

    if (scaleFactor > 1) {
      console.warn(`⚠️ 模型太小（${maxDimOriginal.toFixed(6)}），自适应放大${scaleFactor.toFixed(2)}倍`)
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

    // 调整相机位置/near/far 以适应模型
    const fitBox = new THREE.Box3().setFromObject(model)
    fitCameraToBox(fitBox)
    refreshGridHelper(fitBox)

    scene.add(model)
    console.log('✅ 3D模型已添加到场景')
    console.log('📊 模型信息:', {
      meshCount: meshOriginalPositions.size,
      boundingBox: size,
      center,
      cameraPosition: camera!.position,
      modelPosition: model.position
    })

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
    const scaleFactor = computeAdaptiveScale(maxDimOriginal)

    if (scaleFactor > 1) {
      console.log(`⚠️ 模型太小（${maxDimOriginal.toFixed(6)}），自适应放大${scaleFactor.toFixed(2)}倍`)
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
    fitCameraToBox(new THREE.Box3().setFromObject(model))
    refreshGridHelper(new THREE.Box3().setFromObject(model))

    // 8. 添加到场景
    scene.add(model)
    console.log('✅ 新模型已添加到场景')

    // 9. 初始化显示状态
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
  const manualStatusCache = new Map<string, AssemblyStatus | null>()

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

  // 解析当前零件的手动状态，支持向前继承未装/已装
  const resolveManualStatus = (meshKey: string): AssemblyStatus | null => {
    if (manualStatusCache.has(meshKey)) {
      return manualStatusCache.get(meshKey) || null
    }

    let status: AssemblyStatus | null = null

    // 当前步骤的手动状态
    const stepId = currentStepData.value?.step_id
    if (stepId) {
      const stepStates = partAssemblyStates.value.get(stepId)
      status = stepStates?.get(meshKey) || null
    }

    // 向前继承：未装/正在装/已装都可继承，取最近一次
    if (!status && currentStepIndex.value > 0) {
      for (let i = currentStepIndex.value - 1; i >= 0; i--) {
        const prevStepId = allSteps.value[i]?.step_id
        if (!prevStepId) continue
        const prevStepStates = partAssemblyStates.value.get(prevStepId)
        const prevStatus = prevStepStates?.get(meshKey)
        if (!prevStatus) continue

        if (prevStatus === 'not_installed') {
          status = 'not_installed'
          break
        }
        if (prevStatus === 'installing' || prevStatus === 'installed') {
          status = 'installed'
          break
        }
      }
    }

    manualStatusCache.set(meshKey, status)
    return status
  }

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
    const manualStatus = resolveManualStatus(meshKey)

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

  // 只读/非管理员模式下禁止修改
  if (isReadOnlyMode.value) {
    ElMessage.warning('历史版本为只读，无法修改零件状态')
    closeStatusPopup()
    return
  }
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可修改零件状态')
    closeStatusPopup()
    return
  }

  // ⚠️ 暂时禁用“已装”按钮（不删除逻辑，防止其他路径误调用）
  if (status === 'installed' && disableInstalledStatusOption.value) {
    ElMessage.warning('“已装”状态暂时禁用，请使用“未装 / 正在装”')
    closeStatusPopup()
    return
  }

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

// 丢弃草稿后恢复零件可见性（避免残留隐藏状态）
const restoreAllPartsVisibility = () => {
  if (!model) return
  model.traverse((child: any) => {
    if (!child.isMesh) return
    const meshKey = child.name || child.uuid
    if (!deletedParts.value.has(meshKey)) {
      child.visible = true
    }
  })
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
  fitCameraToBox(new THREE.Box3().setFromObject(model))
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

  // 移动端导航守卫：优先关闭图片预览/抽屉，防止物理返回直接离开
  if (typeof window !== 'undefined' && router) {
    const handlePopState = () => {
      // 如果是手动关闭时触发的 back，则不再重复处理
      if (closingOverlayFromManual) return
      if (overlayStack.length > 0) {
        closingOverlayFromPopstate = true
        const type = overlayStack.pop()
        if (type === 'image') {
          mobileImagePreviewVisible.value = false
          resetMobileImageTransform()
        } else if (type === 'drawer') {
          showDrawingsDrawer.value = false
          showDetailsDrawer.value = false
        }
        closingOverlayFromPopstate = false
      }
    }
    window.addEventListener('popstate', handlePopState)

    // 抽屉打开/关闭时同步历史栈，保证返回键先关抽屉
    watch([showDrawingsDrawer, showDetailsDrawer], ([newDraw, newDetail], [oldDraw, oldDetail]) => {
      if (!isMobile.value) return
      const wasOpen = oldDraw || oldDetail
      const nowOpen = newDraw || newDetail

      if (nowOpen && !wasOpen && typeof window !== 'undefined') {
        try {
          window.history.pushState({ overlay: 'drawer' }, '', window.location.href)
          overlayStack.push('drawer')
        } catch (err) {
          console.warn('⚠️ 抽屉 pushState 失败，返回键行为可能异常:', err)
        }
      }

      if (!nowOpen && wasOpen && overlayStack.length > 0 && typeof window !== 'undefined') {
        if (closingOverlayFromPopstate) return
        const top = overlayStack[overlayStack.length - 1]
        if (top === 'drawer') {
          try {
            closingOverlayFromManual = true
            overlayStack.pop()
            window.history.back()
          } catch (err) {
            console.warn('⚠️ 抽屉关闭回退历史失败:', err)
          } finally {
            closingOverlayFromManual = false
          }
        }
      }
    })
  }
})

onUnmounted(() => {
  cleanup3DViewer()
  sidebarDragCleanup?.()
  if (sidebarResizeRaf !== null) {
    cancelAnimationFrame(sidebarResizeRaf)
    sidebarResizeRaf = null
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
  overlayHistoryDepth = 0
  imageViewerVisible.value = false
  mobileImagePreviewVisible.value = false
  restoreTouchAction()
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
      &.disabled-installed {
        background: #4a90e2;
        opacity: 0.35;
        border: 1px dashed #4a90e2;
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

.installed-disabled-button {
  .disabled-label {
    margin-left: 4px;
    color: #f56c6c !important;
    font-weight: 600;
  }
}

.step-order-hint {
  margin-bottom: 10px;
}

.step-order-list {
  max-height: 420px;
  overflow-y: auto;
  padding-right: 6px;
}

.step-order-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 8px;
  user-select: none;

  &.current {
    background: #fff7e6;
    border: 1px solid #ffd591;
  }
}

.step-order-ghost {
  opacity: 0.45;
}

.step-order-chosen {
  background: #e6f7ff;
}

.drag-handle {
  cursor: grab;
  color: #999;
  font-size: 18px;
  line-height: 1;
}

.step-number {
  color: #409eff;
  font-weight: 600;
}

.step-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  overflow: visible; // 允许折叠按钮在侧栏收起时露出（不压到 3D）
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  min-height: 0;  // ✅ 让 grid 子元素可以收缩
  position: relative;
}

.sidebar-content {
  height: 100%;
  box-sizing: border-box;
  overflow: hidden; // 内容区继续裁剪，避免溢出破坏圆角
  border-radius: 12px;
}

.left-sidebar.is-collapsed .sidebar-content,
.right-sidebar.is-collapsed .sidebar-content {
  display: none; // 收起时隐藏内容，避免出现“残字”
}

.split-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  background: linear-gradient(#eef1ff, #fafbff);
  opacity: 0.18;
  transition: opacity 0.15s;
  user-select: none;
  touch-action: none;
}

.split-handle:hover {
  opacity: 0.9;
}

.split-handle-left {
  right: 0;
}

.split-handle-right {
  left: 0;
}

.split-toggle {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 30;
  height: 28px;
  width: 28px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 0, 0, 0.12);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  cursor: pointer;
  user-select: none;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s, transform 0.15s;
}

.split-toggle:hover {
  transform: translateY(-50%) scale(1.06);
}

.split-toggle.left {
  right: 0;
  border-left: none;
  border-radius: 0 14px 14px 0;
}

.split-toggle.right {
  left: 0;
  border-right: none;
  border-radius: 14px 0 0 14px;
}

/* 默认隐藏：仅在悬浮侧栏边缘/拖拽线时展示 */
.left-sidebar:hover .split-toggle.left,
.right-sidebar:hover .split-toggle.right,
.split-handle:hover + .split-toggle,
.split-toggle:hover {
  opacity: 0.95;
  pointer-events: auto;
}

.left-sidebar {
  .sidebar-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

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

.step-detail-card .step-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  justify-content: flex-start;
}

.right-sidebar {
  .sidebar-content {
    height: 100%;
    padding: 16px;
  }

  .step-detail-card {
    margin-bottom: 16px;

    .step-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 20px;
      justify-content: flex-start;

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

/* 全屏查看图纸时，隐藏全局导航栏并去掉顶部间距 */
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

  /* 移动端：图纸按宽度自适应，去掉 60vh 限高，避免缩小时留白 */
  .drawing-section-full .drawing-item .drawing-image,
  .mobile-drawer-body .drawing-item .drawing-image {
    width: 100%;
    height: auto;
    max-height: none;
    object-fit: contain;
  }
}

.mobile-image-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  z-index: 5000; // 提高层级，确保盖过 Drawer/Mask
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(2px);

  .mobile-image-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    color: #fff;
    font-size: 15px;

    .mobile-image-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  }

  .mobile-image-wrapper {
    flex: 1;
    overflow: hidden;
    padding: 8px;
    touch-action: none;
    position: relative;

    img {
      max-width: none;
      max-height: none;
      width: auto;
      height: auto;
      display: block;
      margin: 0;
      background: #fff;
      border-radius: 6px;
    }
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

.draft-dialog-actions {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.draft-dialog-buttons {
  display: flex;
  gap: 10px;
}

</style>
