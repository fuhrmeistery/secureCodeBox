import { Finding } from "./Finding"
import axios, { AxiosResponse } from "axios"
import * as k8s from "@kubernetes/client-node"

export class ScbApi {
  private readonly FINDINGS_URL_INDEX = 3;

  private kubeConfig: k8s.KubeConfig;
  private k8sApi;

  constructor() {
    this.kubeConfig = new k8s.KubeConfig();
    this.kubeConfig.loadFromCluster();
    this.k8sApi = this.kubeConfig.makeApiClient(k8s.CustomObjectsApi);
  }

  private downloadFile(url: string): Promise<AxiosResponse<any>> {
    return axios.get(url);
  }

  public getFindings(): Promise<void | Array<Finding>> {
    const findingsUrl = process.argv[3];
    return this.downloadFile(findingsUrl).then(({ data: findings }) => {
      console.log(`Fetched ${findings.length} findings from the file storage`);
    });
  }

  private uploadFile(url: string, fileContents: string) {
    return axios
      .put(url, fileContents, {
        headers: { "content-type": "" },
      })
      .catch(function (error) {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          console.error(
            `File Upload Failed with Response Code: ${error.response.status}`
          );
          console.error(`Error Response Body: ${error.response.data}`);
        } else if (error.request) {
          console.error(
            "No response received from FileStorage when uploading finding"
          );
          console.error(error);
        } else {
          // Something happened in setting up the request that triggered an Error
          console.log("Error", error.message);
        }
        process.exit(1);
      });
  }

  public updateRawResults(fileContents) {
    const rawResultUploadUrl = process.argv[4];
    if (rawResultUploadUrl === undefined) {
      console.error(
        "Tried to upload RawResults but didn't find a valid URL to upload the findings to."
      );
      console.error("This probably means that this hook is a ReadOnly hook.");
      console.error(
        "If you want to change RawResults you'll need to use a ReadAndWrite Hook."
      );
    }
    return this.uploadFile(rawResultUploadUrl, fileContents);
  }
}
