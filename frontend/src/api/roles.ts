import request from '@/utils/request'

export interface Role {
  id: string
  name: string
  code: string
  description?: string
  builtIn: boolean
  createdAt: string
  updatedAt: string
}

export interface RoleWithDatasets extends Role {
  datasetIds: string[]
}

export const roleApi = {
  getRoles() {
    return request.get('/roles')
  },
  createRole(data: { name: string; code: string; description?: string }) {
    return request.post('/roles', data)
  },
  updateRole(roleId: string, data: { name?: string; description?: string }) {
    return request.put(`/roles/${roleId}`, data)
  },
  deleteRole(roleId: string) {
    return request.delete(`/roles/${roleId}`)
  },
  getRoleDatasets(roleId: string) {
    return request.get(`/roles/${roleId}/datasets`)
  },
  updateRoleDatasets(roleId: string, datasetIds: string[]) {
    return request.put(`/roles/${roleId}/datasets`, datasetIds)
  }
}

